using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEngine;

namespace AmarIbrahim.AdmRecorder
{
    // Collects position blocks for every AudioObject during a take and writes session.json.
    public class SessionRecorder : MonoBehaviour
    {
        [SerializeField]
        private string sessionTitle = "Untitled Session";

        [SerializeField]
        [Tooltip("Where takes are saved, relative to the Unity project folder. Each take gets its own session_<timestamp> subfolder.")]
        private string outputFolder = "Assets/Sessions";

        [SerializeField]
        private int bitDepth = 24;

        public string OutputFolder => outputFolder;
        public string LastOutputPath { get; private set; }

        private IReadOnlyList<AudioObject> _objects;
        private Dictionary<AudioObject, List<BlockData>> _blocks;
        private float _sessionDuration;
        private int _blockDurationSamples;
        private float _sceneRadius;
        private bool _isRecording;

        public void BeginRecording(
            IReadOnlyList<AudioObject> objects,
            float sessionDuration,
            int blockDurationSamples,
            float sceneRadius)
        {
            _objects = objects;
            _sessionDuration = sessionDuration;
            _blockDurationSamples = blockDurationSamples;
            _sceneRadius = sceneRadius;

            _blocks = new Dictionary<AudioObject, List<BlockData>>();
            foreach (var obj in _objects)
                _blocks[obj] = new List<BlockData>();

            _isRecording = true;
        }

        public void AccumulateBlock(PositionReport report)
        {
            if (!_isRecording) return;
            if (!_blocks.ContainsKey(report.source)) return;

            float rtime = report.sessionTime;
            if (rtime >= _sessionDuration) return; // Past the end of the stems — nothing left to describe.

            var list = _blocks[report.source];

            // Seal the duration of the previous block now that we know its end time.
            if (list.Count > 0)
            {
                var prev = list[list.Count - 1];
                float prevDuration = rtime - prev.rtime;
                if (prevDuration <= 0f) return; // Duplicate or out-of-order — skip.
                prev.duration = prevDuration;
                list[list.Count - 1] = prev;
            }

            list.Add(new BlockData
            {
                rtime = rtime,
                duration = 0f, // Sealed when the next block arrives or on StopRecording.
                x = report.worldPosition.x,
                y = report.worldPosition.y,
                z = report.worldPosition.z,
                gain = 1.0f
            });
        }

        public void StopRecording()
        {
            if (!_isRecording) return;
            _isRecording = false;

            // The last block of every object runs to the end of the session.
            foreach (var obj in _objects)
            {
                var list = _blocks[obj];
                if (list.Count == 0) continue;

                var last = list[list.Count - 1];
                last.duration = Mathf.Max(0f, _sessionDuration - last.rtime);
                list[list.Count - 1] = last;
            }

            LastOutputPath = WriteJson(BuildJson());
            Debug.Log($"[AdmRecorder] Session saved to: {LastOutputPath}");
        }

        private string BuildJson()
        {
            var sb = new StringBuilder();
            sb.AppendLine("{");
            sb.AppendLine("  \"version\": \"1.0\",");
            sb.AppendLine("  \"session\": {");
            sb.AppendLine($"    \"title\": {JsonString(sessionTitle)},");
            sb.AppendLine($"    \"sampleRate\": 48000,");
            sb.AppendLine($"    \"bitDepth\": {bitDepth},");
            sb.AppendLine($"    \"duration\": {F(_sessionDuration)},");
            sb.AppendLine($"    \"blockDurationSamples\": {_blockDurationSamples},");
            sb.AppendLine($"    \"sceneRadius\": {F(_sceneRadius)}");
            sb.AppendLine("  },");
            sb.AppendLine("  \"objects\": [");

            for (int i = 0; i < _objects.Count; i++)
            {
                var obj = _objects[i];
                var list = _blocks[obj];
                bool lastObj = i == _objects.Count - 1;

                sb.AppendLine("    {");
                sb.AppendLine($"      \"id\": {JsonString(obj.ObjectId)},");
                sb.AppendLine($"      \"name\": {JsonString(obj.TrackName)},");
                sb.AppendLine($"      \"stemFile\": {JsonString(obj.StemFileName)},");
                sb.AppendLine($"      \"gain\": 1.0,");
                sb.AppendLine($"      \"start\": 0.0,");
                sb.AppendLine($"      \"duration\": {F(_sessionDuration)},");
                sb.AppendLine("      \"blocks\": [");

                for (int b = 0; b < list.Count; b++)
                {
                    var blk = list[b];
                    bool lastBlk = b == list.Count - 1;
                    sb.Append("        {");
                    sb.Append($" \"rtime\": {F(blk.rtime)},");
                    sb.Append($" \"duration\": {F(blk.duration)},");
                    sb.Append($" \"x\": {F(blk.x)},");
                    sb.Append($" \"y\": {F(blk.y)},");
                    sb.Append($" \"z\": {F(blk.z)},");
                    sb.Append($" \"gain\": 1.0");
                    sb.AppendLine(lastBlk ? " }" : " },");
                }

                sb.AppendLine("      ]");
                sb.AppendLine(lastObj ? "    }" : "    },");
            }

            sb.AppendLine("  ]");
            sb.Append("}");
            return sb.ToString();
        }

        private string WriteJson(string json)
        {
            string dir = Path.Combine(SessionLoader.ResolveProjectPath(outputFolder),
                "session_" + DateTime.Now.ToString("yyyy-MM-dd_HHmmss"));

            Directory.CreateDirectory(dir);
            string path = Path.Combine(dir, "session.json");
            File.WriteAllText(path, json, Encoding.UTF8);
            return path;
        }

        // Format float with 6 decimal places, invariant culture.
        private static string F(float v) =>
            v.ToString("F6", CultureInfo.InvariantCulture);

        private static string JsonString(string s) =>
            "\"" + s.Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"";
    }
}
