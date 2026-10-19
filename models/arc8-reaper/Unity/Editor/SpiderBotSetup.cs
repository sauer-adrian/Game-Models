using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;
using UnityEngine.Rendering;

// Menu: Tools > SpiderBot > Build Prefabs
// Creates materials (Built-in / URP / HDRP), an Animator Controller and one prefab per colour palette.
public static class SpiderBotSetup
{
    static readonly string[] Palettes = { "Obsidian", "Rust", "Void" };

    [MenuItem("Tools/SpiderBot/Build Prefabs")]
    public static void Build()
    {
        string fbx = AssetDatabase.FindAssets("SpiderBot t:Model")
            .Select(AssetDatabase.GUIDToAssetPath).FirstOrDefault(p => p.EndsWith("SpiderBot.fbx"));
        if (fbx == null) { Debug.LogError("SpiderBot.fbx not found in the project."); return; }
        string root = Path.GetDirectoryName(fbx).Replace('\\', '/');
        string texDir = root + "/Textures";
        EnsureFolder(root, "Materials");
        EnsureFolder(root, "Prefabs");

        // texture import settings
        foreach (var guid in AssetDatabase.FindAssets("T_SpiderBot t:Texture2D", new[] { texDir }))
        {
            string p = AssetDatabase.GUIDToAssetPath(guid);
            var ti = (TextureImporter)AssetImporter.GetAtPath(p);
            bool linear = p.Contains("MetallicSmoothness");
            if (ti.sRGBTexture == !linear) continue;
            ti.sRGBTexture = !linear;
            ti.SaveAndReimport();
        }

        var clips = AssetDatabase.LoadAllAssetsAtPath(fbx).OfType<AnimationClip>()
            .Where(c => !c.name.StartsWith("__preview__")).ToDictionary(c => c.name);
        var controller = BuildController(root + "/SpiderBot.controller", clips);

        var model = AssetDatabase.LoadAssetAtPath<GameObject>(fbx);
        var ms = AssetDatabase.LoadAssetAtPath<Texture2D>($"{texDir}/T_SpiderBot_MetallicSmoothness.png");
        foreach (var pal in Palettes)
        {
            var mat = BuildMaterial($"{root}/Materials/M_SpiderBot_{pal}.mat",
                AssetDatabase.LoadAssetAtPath<Texture2D>($"{texDir}/T_SpiderBot_{pal}_Albedo.png"),
                AssetDatabase.LoadAssetAtPath<Texture2D>($"{texDir}/T_SpiderBot_{pal}_Emission.png"), ms);

            var go = (GameObject)PrefabUtility.InstantiatePrefab(model);
            go.name = $"SpiderBot_{pal}";
            foreach (var r in go.GetComponentsInChildren<Renderer>()) r.sharedMaterial = mat;
            var anim = go.GetComponent<Animator>();
            if (anim == null) anim = go.AddComponent<Animator>();
            anim.runtimeAnimatorController = controller;
            anim.applyRootMotion = false;
            if (!go.GetComponent<SpiderBotController>()) go.AddComponent<SpiderBotController>();
            PrefabUtility.SaveAsPrefabAsset(go, $"{root}/Prefabs/SpiderBot_{pal}.prefab");
            Object.DestroyImmediate(go);
        }
        AssetDatabase.SaveAssets();
        Debug.Log($"SpiderBot: built 3 prefabs in {root}/Prefabs");
    }

    static void EnsureFolder(string parent, string name)
    {
        if (!AssetDatabase.IsValidFolder($"{parent}/{name}")) AssetDatabase.CreateFolder(parent, name);
    }

    static Material BuildMaterial(string path, Texture2D albedo, Texture2D emission, Texture2D ms)
    {
        var rp = GraphicsSettings.currentRenderPipeline;
        string kind = rp == null ? "BIRP" : rp.GetType().Name.Contains("HD") ? "HDRP" : "URP";
        var shader = Shader.Find(kind == "HDRP" ? "HDRP/Lit" : kind == "URP" ? "Universal Render Pipeline/Lit" : "Standard");
        var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (mat == null) { mat = new Material(shader); AssetDatabase.CreateAsset(mat, path); }
        else mat.shader = shader;
        Color glow = Color.white * 4f;
        if (kind == "HDRP")
        {
            mat.SetTexture("_BaseColorMap", albedo);
            mat.SetTexture("_EmissiveColorMap", emission);
            mat.SetColor("_EmissiveColor", Color.white * 10f);
            mat.SetFloat("_Metallic", 0.7f); mat.SetFloat("_Smoothness", 0.55f);
        }
        else
        {
            mat.SetTexture(kind == "URP" ? "_BaseMap" : "_MainTex", albedo);
            mat.SetTexture("_MetallicGlossMap", ms);
            mat.EnableKeyword(kind == "URP" ? "_METALLICSPECGLOSSMAP" : "_METALLICGLOSSMAP");
            mat.SetFloat("_Smoothness", 1f); mat.SetFloat("_GlossMapScale", 1f);
            mat.SetTexture("_EmissionMap", emission);
            mat.SetColor("_EmissionColor", glow);
            mat.EnableKeyword("_EMISSION");
            mat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
        }
        EditorUtility.SetDirty(mat);
        return mat;
    }

    static AnimatorController BuildController(string path, System.Collections.Generic.Dictionary<string, AnimationClip> clips)
    {
        AssetDatabase.DeleteAsset(path);
        var ac = AnimatorController.CreateAnimatorControllerAtPath(path);
        ac.AddParameter("Speed", AnimatorControllerParameterType.Float);
        ac.AddParameter("Attack", AnimatorControllerParameterType.Trigger);
        ac.AddParameter("Hit", AnimatorControllerParameterType.Trigger);
        ac.AddParameter("Threat", AnimatorControllerParameterType.Trigger);
        ac.AddParameter("Dead", AnimatorControllerParameterType.Bool);
        var sm = ac.layers[0].stateMachine;

        var loco = ac.CreateBlendTreeInController("Locomotion", out BlendTree tree, 0);
        tree.blendType = BlendTreeType.Simple1D;
        tree.blendParameter = "Speed";
        tree.useAutomaticThresholds = false;
        tree.AddChild(clips["Idle"], 0f);
        tree.AddChild(clips["Walk"], SpiderBotController.WalkClipSpeed);
        tree.AddChild(clips["Run"], SpiderBotController.RunClipSpeed);
        sm.defaultState = loco;

        var attack = sm.AddState("Attack"); attack.motion = clips["Attack"];
        var hit = sm.AddState("Hit"); hit.motion = clips["Hit"];
        var death = sm.AddState("Death"); death.motion = clips["Death"];
        var threat = sm.AddState("Threat"); threat.motion = clips["Threat"];

        var t = loco.AddTransition(attack); t.AddCondition(AnimatorConditionMode.If, 0, "Attack");
        t.hasExitTime = false; t.duration = 0.1f;
        t = attack.AddTransition(loco); t.hasExitTime = true; t.exitTime = 0.9f; t.duration = 0.15f;

        t = loco.AddTransition(threat); t.AddCondition(AnimatorConditionMode.If, 0, "Threat");
        t.hasExitTime = false; t.duration = 0.1f;
        t = threat.AddTransition(loco); t.hasExitTime = true; t.exitTime = 0.92f; t.duration = 0.15f;
        t = threat.AddTransition(attack); t.AddCondition(AnimatorConditionMode.If, 0, "Attack");
        t.hasExitTime = false; t.duration = 0.08f;

        t = sm.AddAnyStateTransition(hit);
        t.AddCondition(AnimatorConditionMode.If, 0, "Hit");
        t.AddCondition(AnimatorConditionMode.IfNot, 0, "Dead");
        t.hasExitTime = false; t.duration = 0.05f; t.canTransitionToSelf = true;
        t = hit.AddTransition(loco); t.hasExitTime = true; t.exitTime = 0.85f; t.duration = 0.15f;

        t = sm.AddAnyStateTransition(death);
        t.AddCondition(AnimatorConditionMode.If, 0, "Dead");
        t.hasExitTime = false; t.duration = 0.1f; t.canTransitionToSelf = false;
        return ac;
    }
}
