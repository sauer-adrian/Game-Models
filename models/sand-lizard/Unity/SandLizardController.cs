using UnityEngine;

// Drives the Sand Lizard Animator. Speeds are in world metres per second and account for the
// object's scale, so a lizard scaled up 3x walks 3x faster without foot sliding.
// Tick "Demo Input" to test: WASD move/turn, Shift run, P push-ups, B burrow/emerge, K die.
[RequireComponent(typeof(Animator))]
public class SandLizardController : MonoBehaviour
{
    // ground speed (m/s at scale 1) at which each looping clip has no foot sliding
    public const float WalkClipSpeed = 0.101f;
    public const float RunClipSpeed = 0.633f;
    public const float BurrowSeconds = 36f / 30f;

    [Header("Animation")]
    public float speedDamp = 0.08f;

    [Header("Testing")]
    public bool demoInput = false;
    public float demoTurnSpeed = 220f;

    public bool IsDead { get; private set; }
    public bool IsBurrowed { get; private set; }
    public float Scale => Mathf.Max(0.0001f, transform.lossyScale.y);
    public float WalkSpeed => WalkClipSpeed * Scale;
    public float RunSpeed => RunClipSpeed * Scale;

    static readonly int SpeedId = Animator.StringToHash("Speed");
    static readonly int PushUpsId = Animator.StringToHash("PushUps");
    static readonly int BurrowedId = Animator.StringToHash("Burrowed");
    static readonly int DeadId = Animator.StringToHash("Dead");

    Animator anim;

    void Awake() => anim = GetComponent<Animator>();

    /// <summary>Ground speed in world metres per second (0 = idle).</summary>
    public void SetSpeed(float worldMetersPerSecond)
    {
        float v = (IsDead || IsBurrowed) ? 0f : worldMetersPerSecond / Scale;
        anim.SetFloat(SpeedId, v, speedDamp, Time.deltaTime);
    }

    /// <summary>Current animated speed in world metres per second (use it to move the transform).</summary>
    public float AnimatedSpeed => anim.GetFloat(SpeedId) * Scale;

    public void PushUps() { if (!IsDead && !IsBurrowed) anim.SetTrigger(PushUpsId); }
    public void Burrow() { if (IsDead) return; IsBurrowed = true; anim.SetFloat(SpeedId, 0f); anim.SetBool(BurrowedId, true); }
    public void Emerge() { if (IsDead) return; IsBurrowed = false; anim.SetBool(BurrowedId, false); }

    public void Die()
    {
        if (IsDead) return;
        IsDead = true;
        anim.SetFloat(SpeedId, 0f);
        anim.SetBool(DeadId, true);
    }

    void Update()
    {
        if (!demoInput || IsDead) return;
        float fwd = 0f, turn = 0f; bool run = false, push = false, burrow = false, die = false;
#if ENABLE_INPUT_SYSTEM
        var k = UnityEngine.InputSystem.Keyboard.current;
        if (k != null)
        {
            fwd = (k.wKey.isPressed ? 1 : 0) - (k.sKey.isPressed ? 1 : 0);
            turn = (k.dKey.isPressed ? 1 : 0) - (k.aKey.isPressed ? 1 : 0);
            run = k.leftShiftKey.isPressed; push = k.pKey.wasPressedThisFrame;
            burrow = k.bKey.wasPressedThisFrame; die = k.kKey.wasPressedThisFrame;
        }
#elif ENABLE_LEGACY_INPUT_MANAGER
        fwd = Input.GetAxisRaw("Vertical"); turn = Input.GetAxisRaw("Horizontal");
        run = Input.GetKey(KeyCode.LeftShift); push = Input.GetKeyDown(KeyCode.P);
        burrow = Input.GetKeyDown(KeyCode.B); die = Input.GetKeyDown(KeyCode.K);
#endif
        if (burrow) { if (IsBurrowed) Emerge(); else Burrow(); }
        if (push) PushUps();
        if (die) Die();
        if (IsBurrowed) return;
        SetSpeed(Mathf.Max(0f, fwd) * (run ? RunSpeed : WalkSpeed));
        transform.Rotate(0f, turn * demoTurnSpeed * Time.deltaTime, 0f);
        transform.position += transform.forward * AnimatedSpeed * Time.deltaTime;
    }
}
