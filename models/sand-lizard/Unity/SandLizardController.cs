using UnityEngine;

// Drives the Sand Lizard Animator. Speeds are in world metres per second and account for the
// object's scale, so a lizard scaled up 3x walks 3x faster without foot sliding.
// Turning is automatic: the controller measures how fast the object yaws and plays the stepping
// TurnLeft/TurnRight clips (paced to the real turn rate) and bends the spine and tail into moving turns.
// Tick "Demo Input" to test: WASD move/turn, Shift run, P push-ups, B burrow/emerge, K die.
[RequireComponent(typeof(Animator))]
public class SandLizardController : MonoBehaviour
{
    // ground speed (m/s at scale 1) at which each looping clip has no foot sliding
    public const float WalkClipSpeed = 0.101f;
    public const float RunClipSpeed = 0.633f;
    public const float BurrowSeconds = 36f / 30f;
    // yaw rate (deg/s) at which the turn clips' planted feet don't slip
    public const float TurnClipDegPerSec = 89.52f;

    [Header("Animation")]
    public float speedDamp = 0.08f;
    public float turnDamp = 0.1f;
    [Tooltip("How far the spine and tail curve into turns while moving.")] [Range(0, 2)] public float turnBend = 1f;

    [Header("Testing")]
    public bool demoInput = false;
    public float demoTurnSpeed = 140f;

    public bool IsDead { get; private set; }
    public bool IsBurrowed { get; private set; }
    public float Scale => Mathf.Max(0.0001f, transform.lossyScale.y);
    public float WalkSpeed => WalkClipSpeed * Scale;
    public float RunSpeed => RunClipSpeed * Scale;

    static readonly int SpeedId = Animator.StringToHash("Speed");
    static readonly int TurnId = Animator.StringToHash("Turn");
    static readonly int LocoRateId = Animator.StringToHash("LocoRate");
    static readonly int PushUpsId = Animator.StringToHash("PushUps");
    static readonly int BurrowedId = Animator.StringToHash("Burrowed");
    static readonly int DeadId = Animator.StringToHash("Dead");

    Animator anim;
    float lastYaw, yawRate;          // deg/s, + = turning right
    Transform[] bendBones;
    static readonly string[] BendNames = { "Chest", "Neck", "Hips", "Tail1", "Tail2", "Tail3", "Tail4" };
    static readonly float[] BendAmount = { 1f, 0.7f, -0.45f, -0.35f, -0.45f, -0.5f, -0.5f };

    /// <summary>Measured yaw rate in degrees per second (positive = turning right).</summary>
    public float YawRate => yawRate;

    void Awake()
    {
        anim = GetComponent<Animator>();
        lastYaw = transform.eulerAngles.y;
        bendBones = new Transform[BendNames.Length];
        for (int i = 0; i < BendNames.Length; i++) bendBones[i] = FindDeep(transform, BendNames[i]);
    }

    static Transform FindDeep(Transform t, string name)
    {
        if (t.name == name) return t;
        foreach (Transform c in t) { var r = FindDeep(c, name); if (r != null) return r; }
        return null;
    }

    // Feed the measured turn rate to the blend tree. When pivoting on the spot faster than the clip's
    // rate, the whole locomotion state speeds up so the feet keep pace instead of sliding.
    void UpdateTurnParams()
    {
        if (anim == null || anim.runtimeAnimatorController == null) return;
        float t = (IsDead || IsBurrowed) ? 0f : yawRate;
        float clampTurn = Mathf.Clamp(t, -TurnClipDegPerSec, TurnClipDegPerSec);
        anim.SetFloat(TurnId, clampTurn, turnDamp, Time.deltaTime);
        float moving = Mathf.Clamp01(anim.GetFloat(SpeedId) / WalkClipSpeed);
        float spin = Mathf.Max(1f, Mathf.Abs(t) / TurnClipDegPerSec);
        anim.SetFloat(LocoRateId, Mathf.Lerp(spin, 1f, moving));
    }

    void LateUpdate()
    {
        float yaw = transform.eulerAngles.y;
        float dt = Mathf.Max(Time.deltaTime, 1e-5f);
        yawRate = Mathf.Lerp(yawRate, Mathf.DeltaAngle(lastYaw, yaw) / dt, 1f - Mathf.Exp(-12f * dt));
        lastYaw = yaw;
        // curve the spine and tail into the turn while walking or running (after the Animator has posed the bones)
        if (turnBend <= 0f || IsDead || IsBurrowed) return;
        float moving = Mathf.Clamp01(anim.GetFloat(SpeedId) / WalkClipSpeed);
        float bend = Mathf.Clamp(yawRate * 0.085f, -18f, 18f) * moving * turnBend;
        if (Mathf.Abs(bend) < 0.01f) return;
        Vector3 up = transform.up;
        for (int i = 0; i < bendBones.Length; i++)
            if (bendBones[i] != null) bendBones[i].rotation = Quaternion.AngleAxis(bend * BendAmount[i], up) * bendBones[i].rotation;
    }

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
        UpdateTurnParams();
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
