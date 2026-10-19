using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;
using UnityEngine.Rendering;

// Menu: Tools > Sand Lizard > Build Prefabs
// Creates materials (Built-in / URP / HDRP), an Animator Controller and one prefab per colour scheme.
public static class SandLizardSetup
{
    static readonly string[] Palettes = { "Desert", "Dune", "Ember" };

    [MenuItem("Tools/Sand Lizard/Build Prefabs")]
    public static void Build()
    {
        string fbx = AssetDatabase.FindAssets("SandLizard t:Model")
            .Select(AssetDatabase.GUIDToAssetPath).FirstOrDefault(p => p.EndsWith("SandLizard.fbx"));
        if (fbx == null) { Debug.LogError("SandLizard.fbx not found in the project."); return; }
        string root = Path.GetDirectoryName(fbx).Replace('\\', '/');
        string texDir = root + "/Textures";
        EnsureFolder(root, "Materials");
        EnsureFolder(root, "Prefabs");

        foreach (var guid in AssetDatabase.FindAssets("T_SandLizard t:Texture2D", new[] { texDir }))
        {
            string p = AssetDatabase.GUIDToAssetPath(guid);
            var ti = (TextureImporter)AssetImporter.GetAtPath(p);
            bool linear = p.Contains("MetallicSmoothness");
            bool changed = false;
            if (ti.sRGBTexture == linear) { ti.sRGBTexture = !linear; changed = true; }
            if (ti.filterMode != FilterMode.Point) { ti.filterMode = FilterMode.Point; changed = true; }
            if (ti.mipmapEnabled) { ti.mipmapEnabled = false; changed = true; }
            if (changed) ti.SaveAndReimport();
        }

        var clips = AssetDatabase.LoadAllAssetsAtPath(fbx).OfType<AnimationClip>()
            .Where(c => !c.name.StartsWith("__preview__")).ToDictionary(c => c.name);
        foreach (var need in new[] { "Idle", "Walk", "Run", "PushUps", "Burrow", "Emerge", "Death" })
            if (!clips.ContainsKey(need)) { Debug.LogError($"Clip '{need}' missing. Reimport SandLizard.fbx after adding the scripts."); return; }
        var controller = BuildController(root + "/SandLizard.controller", clips);

        var model = AssetDatabase.LoadAssetAtPath<GameObject>(fbx);
        var ms = AssetDatabase.LoadAssetAtPath<Texture2D>($"{texDir}/T_SandLizard_MetallicSmoothness.png");
        foreach (var pal in Palettes)
        {
            var mat = BuildMaterial($"{root}/Materials/M_SandLizard_{pal}.mat",
                AssetDatabase.LoadAssetAtPath<Texture2D>($"{texDir}/T_SandLizard_{pal}_Albedo.png"), ms);
            var go = (GameObject)PrefabUtility.InstantiatePrefab(model);
            go.name = $"SandLizard_{pal}";
            foreach (var r in go.GetComponentsInChildren<Renderer>()) r.sharedMaterial = mat;
            var anim = go.GetComponent<Animator>();
            if (anim == null) anim = go.AddComponent<Animator>();
            anim.runtimeAnimatorController = controller;
            anim.applyRootMotion = false;
            if (!go.GetComponent<SandLizardController>()) go.AddComponent<SandLizardController>();
            if (!go.GetComponent<SandLizardAI>()) go.AddComponent<SandLizardAI>();
            PrefabUtility.SaveAsPrefabAsset(go, $"{root}/Prefabs/SandLizard_{pal}.prefab");
            Object.DestroyImmediate(go);
        }
        AssetDatabase.SaveAssets();
        Debug.Log($"Sand Lizard: built 3 prefabs in {root}/Prefabs");
    }

    static void EnsureFolder(string parent, string name)
    {
        if (!AssetDatabase.IsValidFolder($"{parent}/{name}")) AssetDatabase.CreateFolder(parent, name);
    }

    static Material BuildMaterial(string path, Texture2D albedo, Texture2D ms)
    {
        var rp = GraphicsSettings.currentRenderPipeline;
        string kind = rp == null ? "BIRP" : rp.GetType().Name.Contains("HD") ? "HDRP" : "URP";
        var shader = Shader.Find(kind == "HDRP" ? "HDRP/Lit" : kind == "URP" ? "Universal Render Pipeline/Lit" : "Standard");
        var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (mat == null) { mat = new Material(shader); AssetDatabase.CreateAsset(mat, path); }
        else mat.shader = shader;
        if (kind == "HDRP")
        {
            mat.SetTexture("_BaseColorMap", albedo);
            mat.SetFloat("_Metallic", 0f); mat.SetFloat("_Smoothness", 0.35f);
        }
        else
        {
            mat.SetTexture(kind == "URP" ? "_BaseMap" : "_MainTex", albedo);
            mat.SetTexture("_MetallicGlossMap", ms);
            mat.EnableKeyword(kind == "URP" ? "_METALLICSPECGLOSSMAP" : "_METALLICGLOSSMAP");
            mat.SetFloat("_Smoothness", 1f); mat.SetFloat("_GlossMapScale", 1f);
        }
        EditorUtility.SetDirty(mat);
        return mat;
    }

    static AnimatorController BuildController(string path, Dictionary<string, AnimationClip> clips)
    {
        AssetDatabase.DeleteAsset(path);
        var ac = AnimatorController.CreateAnimatorControllerAtPath(path);
        ac.AddParameter("Speed", AnimatorControllerParameterType.Float);
        ac.AddParameter("PushUps", AnimatorControllerParameterType.Trigger);
        ac.AddParameter("Burrowed", AnimatorControllerParameterType.Bool);
        ac.AddParameter("Dead", AnimatorControllerParameterType.Bool);
        var sm = ac.layers[0].stateMachine;

        var loco = ac.CreateBlendTreeInController("Locomotion", out BlendTree tree, 0);
        tree.blendType = BlendTreeType.Simple1D;
        tree.blendParameter = "Speed";
        tree.useAutomaticThresholds = false;
        tree.AddChild(clips["Idle"], 0f);
        tree.AddChild(clips["Walk"], SandLizardController.WalkClipSpeed);
        tree.AddChild(clips["Run"], SandLizardController.RunClipSpeed);
        sm.defaultState = loco;

        var push = sm.AddState("PushUps"); push.motion = clips["PushUps"];
        var burrow = sm.AddState("Burrow"); burrow.motion = clips["Burrow"];
        var emerge = sm.AddState("Emerge"); emerge.motion = clips["Emerge"];
        var death = sm.AddState("Death"); death.motion = clips["Death"];

        var t = loco.AddTransition(push); t.AddCondition(AnimatorConditionMode.If, 0, "PushUps");
        t.hasExitTime = false; t.duration = 0.1f;
        t = push.AddTransition(loco); t.hasExitTime = true; t.exitTime = 0.95f; t.duration = 0.1f;

        foreach (var from in new[] { loco, push })
        {
            t = from.AddTransition(burrow); t.AddCondition(AnimatorConditionMode.If, 0, "Burrowed");
            t.hasExitTime = false; t.duration = 0.08f;
        }
        t = burrow.AddTransition(emerge); t.AddCondition(AnimatorConditionMode.IfNot, 0, "Burrowed");
        t.hasExitTime = false; t.duration = 0.05f;
        t = emerge.AddTransition(loco); t.hasExitTime = true; t.exitTime = 0.95f; t.duration = 0.1f;

        t = sm.AddAnyStateTransition(death);
        t.AddCondition(AnimatorConditionMode.If, 0, "Dead");
        t.hasExitTime = false; t.duration = 0.08f; t.canTransitionToSelf = false;
        return ac;
    }
}
