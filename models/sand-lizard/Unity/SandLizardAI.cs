using UnityEngine;

// Ambient critter behaviour: idles (sometimes with a push-up display), wanders around its home spot,
// flees from a threat, and dives into the sand if the threat gets too close, popping up somewhere else.
// The threat defaults to the GameObject tagged "Player". Distances scale with the lizard's size.
[RequireComponent(typeof(SandLizardController))]
public class SandLizardAI : MonoBehaviour
{
    [Header("Threat")]
    public Transform threat;
    [Tooltip("Flee when the threat is closer than this (metres at scale 1).")] public float noticeDistance = 2.5f;
    [Tooltip("Stop fleeing once the threat is this far away.")] public float safeDistance = 4.5f;
    [Tooltip("Dive into the sand when the threat is this close.")] public float panicDistance = 0.9f;
    [Tooltip("Dive anyway after fleeing this long.")] public float maxFleeSeconds = 3f;

    [Header("Wandering")]
    public float wanderRadius = 2.5f;
    public Vector2 idleSeconds = new Vector2(1.5f, 4f);
    [Range(0, 1)] public float pushUpChance = 0.35f;
    [Range(0, 1)] public float runChance = 0.2f;
    public Vector2 hideSeconds = new Vector2(3f, 6f);

    [Header("Movement")]
    [Tooltip("Max turn rate (deg/s) while running flat out.")] public float runTurnSpeed = 240f;
    [Tooltip("Pivot rate on the spot, as a multiple of the turn clip's rate (calm / fleeing).")]
    public Vector2 pivotMultiplier = new Vector2(1.15f, 2f);
    public LayerMask groundMask = ~0;
    public LayerMask obstacleMask = ~0;
    [Tooltip("Tilt to match the ground slope.")] public bool alignToGround = true;

    enum State { Idle, Wander, Flee, Burrowing, Hidden, Emerging, Dead }
    State state;
    float timer, fleeTimer;
    Vector3 home, goal;
    bool running;
    SandLizardController ctl;
    Renderer[] renderers;

    float S => ctl.Scale;

    void Awake()
    {
        ctl = GetComponent<SandLizardController>();
        renderers = GetComponentsInChildren<Renderer>();
        home = transform.position;
    }

    void Start()
    {
        if (threat == null)
        {
            var p = GameObject.FindGameObjectWithTag("Player");
            if (p != null) threat = p.transform;
        }
        Enter(State.Idle);
    }

    float ThreatDistance()
    {
        if (threat == null) return float.PositiveInfinity;
        Vector3 d = threat.position - transform.position; d.y = 0f;
        return d.magnitude;
    }

    void Enter(State s)
    {
        state = s;
        switch (s)
        {
            case State.Idle:
                timer = Random.Range(idleSeconds.x, idleSeconds.y);
                if (Random.value < pushUpChance) ctl.PushUps();
                break;
            case State.Wander:
                goal = PickPoint(home, wanderRadius * S);
                running = Random.value < runChance;
                timer = 12f;
                break;
            case State.Flee:
                fleeTimer = 0f;
                break;
            case State.Burrowing:
                ctl.Burrow(); timer = SandLizardController.BurrowSeconds + 0.1f;
                break;
            case State.Hidden:
                SetVisible(false); timer = Random.Range(hideSeconds.x, hideSeconds.y);
                break;
            case State.Emerging:
                transform.position = Ground(PickPoint(home, wanderRadius * S));
                transform.rotation = Quaternion.Euler(0f, Random.Range(0f, 360f), 0f);
                SetVisible(true); ctl.Emerge(); timer = SandLizardController.BurrowSeconds + 0.1f;
                break;
            case State.Dead:
                ctl.SetSpeed(0f);
                break;
        }
    }

    void Update()
    {
        if (ctl.demoInput) return;
        if (ctl.IsDead) { if (state != State.Dead) Enter(State.Dead); return; }
        float dt = Time.deltaTime, td = ThreatDistance();
        timer -= dt;

        bool canReact = state == State.Idle || state == State.Wander;
        if (canReact && td < noticeDistance * S) Enter(State.Flee);

        switch (state)
        {
            case State.Idle:
                ctl.SetSpeed(0f);
                if (timer <= 0f) Enter(State.Wander);
                break;
            case State.Wander:
            {
                Vector3 to = goal - transform.position; to.y = 0f;
                if (to.magnitude < 0.12f * S || timer <= 0f) { Enter(State.Idle); break; }
                Steer(to, running ? ctl.RunSpeed : ctl.WalkSpeed, dt);
                break;
            }
            case State.Flee:
            {
                fleeTimer += dt;
                if (threat == null) { Enter(State.Idle); break; }
                if (td < panicDistance * S || fleeTimer > maxFleeSeconds) { Enter(State.Burrowing); break; }
                if (td > safeDistance * S) { Enter(State.Idle); break; }
                Vector3 away = transform.position - threat.position; away.y = 0f;
                away = Quaternion.Euler(0f, Mathf.Sin(Time.time * 2.3f + GetInstanceID()) * 35f, 0f) * away;
                Steer(away, ctl.RunSpeed, dt);
                break;
            }
            case State.Burrowing:
                ctl.SetSpeed(0f);
                if (timer <= 0f) Enter(State.Hidden);
                break;
            case State.Hidden:
                if (timer <= 0f && td > noticeDistance * S) Enter(State.Emerging);
                break;
            case State.Emerging:
                if (timer <= 0f) Enter(State.Idle);
                break;
        }
    }

    void Steer(Vector3 dir, float speed, float dt)
    {
        if (dir.sqrMagnitude < 1e-6f) return;
        dir.Normalize();
        // look ahead for walls and rocks; slide along them instead of walking into them
        Vector3 origin = transform.position + Vector3.up * 0.04f * S;
        if (Physics.SphereCast(origin, 0.04f * S, dir, out RaycastHit hit, 0.35f * S, obstacleMask, QueryTriggerInteraction.Ignore)
            && Vector3.Dot(hit.normal, Vector3.up) < 0.6f && !hit.transform.IsChildOf(transform))
        {
            Vector3 n = hit.normal; n.y = 0f;
            dir = Vector3.ProjectOnPlane(dir, n.normalized).normalized;
            if (dir.sqrMagnitude < 0.01f) dir = Vector3.Cross(Vector3.up, n).normalized;
            if (state == State.Wander) goal = PickPoint(home, wanderRadius * S);
        }
        bool urgent = state == State.Flee;
        Quaternion want = Quaternion.LookRotation(dir, Vector3.up);
        Quaternion yawOnly = Quaternion.Euler(0f, transform.eulerAngles.y, 0f);
        float moving = Mathf.Clamp01(ctl.AnimatedSpeed / Mathf.Max(ctl.RunSpeed, 1e-4f));
        float pivot = SandLizardController.TurnClipDegPerSec * (urgent ? pivotMultiplier.y : pivotMultiplier.x);
        Quaternion yaw = Quaternion.RotateTowards(yawOnly, want, Mathf.Lerp(pivot, runTurnSpeed, moving) * dt);
        float angleOff = Quaternion.Angle(yaw, want);
        // big direction changes: pivot on the spot first (stepping turn clip), then go
        float k = angleOff > 50f ? (urgent ? 0.3f : 0f) : Mathf.Clamp(1.15f - angleOff / 63f, 0.2f, 1f);
        ctl.SetSpeed(speed * k);
        Vector3 next = transform.position + (yaw * Vector3.forward) * ctl.AnimatedSpeed * dt;
        Place(next, yaw);
    }

    void Place(Vector3 pos, Quaternion yaw)
    {
        Vector3 up = Vector3.up;
        if (Physics.Raycast(pos + Vector3.up * 0.5f * S, Vector3.down, out RaycastHit hit, 2f * S + 1f, groundMask, QueryTriggerInteraction.Ignore))
        {
            pos.y = hit.point.y;
            if (alignToGround) up = hit.normal;
        }
        Quaternion tilt = Quaternion.FromToRotation(Vector3.up, up);
        transform.SetPositionAndRotation(pos, Quaternion.Slerp(transform.rotation, tilt * yaw, 0.25f));
    }

    Vector3 Ground(Vector3 p)
    {
        if (Physics.Raycast(p + Vector3.up * 2f, Vector3.down, out RaycastHit hit, 6f, groundMask, QueryTriggerInteraction.Ignore))
            p.y = hit.point.y;
        return p;
    }

    static Vector3 PickPoint(Vector3 center, float radius)
    {
        Vector2 r = Random.insideUnitCircle * radius;
        return new Vector3(center.x + r.x, center.y, center.z + r.y);
    }

    void SetVisible(bool v) { foreach (var r in renderers) if (r) r.enabled = v; }

    /// <summary>Kill the lizard (for weapons, traps, stomping...).</summary>
    public void Kill() => ctl.Die();

    void OnDrawGizmosSelected()
    {
        float s = Application.isPlaying && ctl ? S : transform.lossyScale.y;
        Vector3 c = Application.isPlaying ? home : transform.position;
        Gizmos.color = new Color(0.9f, 0.7f, 0.3f, 0.6f); Gizmos.DrawWireSphere(c, wanderRadius * s);
        Gizmos.color = new Color(1f, 0.4f, 0.2f, 0.6f); Gizmos.DrawWireSphere(transform.position, noticeDistance * s);
    }
}
