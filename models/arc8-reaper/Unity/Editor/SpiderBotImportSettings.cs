using UnityEditor;
using UnityEngine;

// Auto-configures SpiderBot.fbx on import: Generic rig, flat normals kept,
// clip names cleaned ("SpiderBot|Walk" -> "Walk") and Idle/Walk/Run set to loop.
public class SpiderBotImportSettings : AssetPostprocessor
{
    static bool IsSpider(string path) =>
        path.Replace('\\', '/').Contains("SpiderBot") &&
        path.EndsWith(".fbx", System.StringComparison.OrdinalIgnoreCase);

    void OnPreprocessModel()
    {
        if (!IsSpider(assetPath)) return;
        var mi = (ModelImporter)assetImporter;
        mi.animationType = ModelImporterAnimationType.Generic;
        mi.importNormals = ModelImporterNormals.Import;
        mi.bakeAxisConversion = true;
        mi.materialImportMode = ModelImporterMaterialImportMode.None; // materials come from the setup menu
    }

    void OnPreprocessAnimation()
    {
        if (!IsSpider(assetPath)) return;
        var mi = (ModelImporter)assetImporter;
        if (mi.clipAnimations != null && mi.clipAnimations.Length > 0) return; // keep your own edits
        var clips = mi.defaultClipAnimations;
        if (clips == null || clips.Length == 0) return;
        foreach (var c in clips)
        {
            string n = c.name;
            int i = n.LastIndexOf('|');
            if (i >= 0) n = n.Substring(i + 1);
            c.name = n;
            c.loopTime = n == "Idle" || n == "Walk" || n == "Run";
        }
        mi.clipAnimations = clips;
    }
}
