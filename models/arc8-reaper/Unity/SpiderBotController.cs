using System.Collections;
using UnityEngine;

// Drives the SpiderBot Animator. Call SetSpeed / Attack / Hit / Die from your AI,
// or tick "Demo Input" to test with WASD + Shift (run), T (threat), Space (attack), H (hit), K (die).
[RequireComponent(typeof(Animator))]
public class SpiderBotController : MonoBehaviour
{
    // ground speed (m/s) at which each looping clip has no foot sliding
    public const float WalkClipSpeed = 0.65f;
    public const float RunClipSpeed = 1.39f;

    [Header("Movement")]
    public float maxSpeed = RunClipSpeed;
    public float turnSpeed = 160f;
    public float speedDamp = 0.12f;

    [Header("Testing")]
    public bool demoInput = false;

    [Header("Death")]
    public float eyeFadeTime = 1.5f;

    public bool IsDead { get; private set; }

    static readonly int SpeedId = Animator.StringToHash("Speed");
    static readonly int AttackId = Animator.StringToHash("Attack");
    static readonly int HitId = Animator.StringToHash("Hit");
    static readonly int ThreatId = Animator.StringToHash("Threat");
    static readonly int DeadId = Animator.StringToHash("Dead");

    Animator anim;
    float currentSpeed;

    void Awake() => anim = GetComponent<Animator>();

    /// <summary>Set the ground speed in metres per second (0 = idle, ~0.7 walk, ~1.4 run).</summary>
    public void SetSpeed(float metersPerSecond)
    {
        currentSpeed = IsDead ? 0f : metersPerSecond;
        anim.SetFloat(SpeedId, currentSpeed, speedDamp, Time.deltaTime);
    }

    public void Attack() { if (!IsDead) anim.SetTrigger(AttackId); }
    public void Hit() { if (!IsDead) anim.SetTrigger(HitId); }
    /// <summary>Rear up with legs spread and fangs flared (play when it spots the player).</summary>
    public void Threaten() { if (!IsDead) anim.SetTrigger(ThreatId); }

    public void Die()
    {
        if (IsDead) return;
        IsDead = true;
        anim.SetFloat(SpeedId, 0f);
        anim.SetBool(DeadId, true);
        StartCoroutine(FadeEyes());
    }

    void Update()
    {
        if (!demoInput || IsDead) return;
        float fwd = 0f, turn = 0f; bool run = false, atk = false, hit = false, die = false, thr = false;
#if ENABLE_INPUT_SYSTEM
        var k = UnityEngine.InputSystem.Keyboard.current;
        if (k != null)
        {
            fwd = (k.wKey.isPressed ? 1 : 0) - (k.sKey.isPressed ? 1 : 0);
            turn = (k.dKey.isPressed ? 1 : 0) - (k.aKey.isPressed ? 1 : 0);
            run = k.leftShiftKey.isPressed; atk = k.spaceKey.wasPressedThisFrame;
            hit = k.hKey.wasPressedThisFrame; die = k.kKey.wasPressedThisFrame;
            thr = k.tKey.wasPressedThisFrame;
        }
#elif ENABLE_LEGACY_INPUT_MANAGER
        fwd = Input.GetAxisRaw("Vertical"); turn = Input.GetAxisRaw("Horizontal");
        run = Input.GetKey(KeyCode.LeftShift); atk = Input.GetKeyDown(KeyCode.Space);
        hit = Input.GetKeyDown(KeyCode.H); die = Input.GetKeyDown(KeyCode.K);
        thr = Input.GetKeyDown(KeyCode.T);
#endif
        float target = Mathf.Max(0f, fwd) * (run ? RunClipSpeed : WalkClipSpeed);
        SetSpeed(target);
        transform.Rotate(0f, turn * turnSpeed * Time.deltaTime, 0f);
        transform.position += transform.forward * anim.GetFloat(SpeedId) * Time.deltaTime;
        if (thr) Threaten();
        if (atk) Attack();
        if (hit) Hit();
        if (die) Die();
    }

    IEnumerator FadeEyes()
    {
        var rends = GetComponentsInChildren<Renderer>();
        var mpb = new MaterialPropertyBlock();
        string prop = rends.Length > 0 && rends[0].sharedMaterial != null &&
                      rends[0].sharedMaterial.HasProperty("_EmissiveColor") ? "_EmissiveColor" : "_EmissionColor";
        Color start = rends.Length > 0 && rends[0].sharedMaterial != null && rends[0].sharedMaterial.HasProperty(prop)
            ? rends[0].sharedMaterial.GetColor(prop) : Color.white;
        yield return new WaitForSeconds(0.4f);
        for (float t = 0; t < 1f; t += Time.deltaTime / Mathf.Max(0.01f, eyeFadeTime))
        {
            // flicker, then fade out
            float flick = t < 0.3f && Random.value < 0.35f ? 0.2f : 1f;
            Color c = Color.Lerp(start, Color.black, t) * flick;
            foreach (var r in rends) { r.GetPropertyBlock(mpb); mpb.SetColor(prop, c); r.SetPropertyBlock(mpb); }
            yield return null;
        }
        foreach (var r in rends) { r.GetPropertyBlock(mpb); mpb.SetColor(prop, Color.black); r.SetPropertyBlock(mpb); }
    }
}
