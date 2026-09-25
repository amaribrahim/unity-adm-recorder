using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using UnityEngine;

namespace AmarIbrahim.AdmRecorder
{
    // Parsed representation of session.json — matches the v1.0 schema.
    public class LoadedSession
    {
        public string title;
        public int sampleRate;
        public int bitDepth;
        public float duration;
        public int blockDurationSamples;
        public float sceneRadius;
        public List<LoadedObject> objects = new List<LoadedObject>();
    }

    public class LoadedObject
    {
        public string id;
        public string name;
        public string stemFile;
        public float gain;
        public float start;
        public float duration;
        public List<LoadedBlock> blocks = new List<LoadedBlock>();
    }

    public class LoadedBlock
    {
        public float rtime;
        public float duration;
        public float x;
        public float y;
        public float z;
        public float gain;
    }

    // Minimal hand-rolled JSON parser for the session.json format.
    // Handles the exact structure written by SessionRecorder — no general-purpose parser needed.
    public static class SessionLoader
    {
        public static LoadedSession Load(string filePath)
        {
            string json = File.ReadAllText(filePath);
            return Parse(json);
        }

        // "Assets/Sessions" → absolute path inside the Unity project folder.
        public static string ResolveProjectPath(string projectRelativePath)
        {
            return Path.GetFullPath(Path.Combine(Application.dataPath, "..", projectRelativePath));
        }

        // Returns the newest session_<timestamp>/session.json under the given project-relative folder.
        public static string FindLatestSessionPath(string projectRelativeFolder)
        {
            string sessionsDir = ResolveProjectPath(projectRelativeFolder);
            if (!Directory.Exists(sessionsDir))
                return null;

            string[] dirs = Directory.GetDirectories(sessionsDir, "session_*");
            if (dirs.Length == 0)
                return null;

            Array.Sort(dirs);
            string latest = dirs[dirs.Length - 1];
            string path = Path.Combine(latest, "session.json");
            return File.Exists(path) ? path : null;
        }

        private static LoadedSession Parse(string json)
        {
            var session = new LoadedSession();
            int pos = 0;

            SkipTo(json, ref pos, "\"title\"");
            session.title = ReadStringValue(json, ref pos);

            SkipTo(json, ref pos, "\"sampleRate\"");
            session.sampleRate = (int)ReadNumberValue(json, ref pos);

            SkipTo(json, ref pos, "\"bitDepth\"");
            session.bitDepth = (int)ReadNumberValue(json, ref pos);

            SkipTo(json, ref pos, "\"duration\"");
            session.duration = ReadNumberValue(json, ref pos);

            SkipTo(json, ref pos, "\"blockDurationSamples\"");
            session.blockDurationSamples = (int)ReadNumberValue(json, ref pos);

            SkipTo(json, ref pos, "\"sceneRadius\"");
            session.sceneRadius = ReadNumberValue(json, ref pos);

            SkipTo(json, ref pos, "\"objects\"");

            // Advance past the opening '[' of the objects array.
            SkipToChar(json, ref pos, '[');
            pos++;

            while (true)
            {
                SkipWhitespace(json, ref pos);
                if (pos >= json.Length || json[pos] == ']') break;
                if (json[pos] == ',') { pos++; continue; }
                if (json[pos] != '{') { pos++; continue; }

                session.objects.Add(ParseObject(json, ref pos));
            }

            return session;
        }

        private static LoadedObject ParseObject(string json, ref int pos)
        {
            // pos is on '{'
            pos++;
            var obj = new LoadedObject();

            SkipTo(json, ref pos, "\"id\"");
            obj.id = ReadStringValue(json, ref pos);

            SkipTo(json, ref pos, "\"name\"");
            obj.name = ReadStringValue(json, ref pos);

            SkipTo(json, ref pos, "\"stemFile\"");
            obj.stemFile = ReadStringValue(json, ref pos);

            SkipTo(json, ref pos, "\"gain\"");
            obj.gain = ReadNumberValue(json, ref pos);

            SkipTo(json, ref pos, "\"start\"");
            obj.start = ReadNumberValue(json, ref pos);

            SkipTo(json, ref pos, "\"duration\"");
            obj.duration = ReadNumberValue(json, ref pos);

            SkipTo(json, ref pos, "\"blocks\"");
            SkipToChar(json, ref pos, '[');
            pos++;

            while (true)
            {
                SkipWhitespace(json, ref pos);
                if (pos >= json.Length || json[pos] == ']') break;
                if (json[pos] == ',') { pos++; continue; }
                if (json[pos] != '{') { pos++; continue; }

                obj.blocks.Add(ParseBlock(json, ref pos));
            }

            // Advance past ']' and closing '}'
            if (pos < json.Length && json[pos] == ']') pos++;
            SkipWhitespace(json, ref pos);
            if (pos < json.Length && json[pos] == '}') pos++;

            return obj;
        }

        private static LoadedBlock ParseBlock(string json, ref int pos)
        {
            // pos is on '{'
            int end = json.IndexOf('}', pos);
            string chunk = json.Substring(pos, end - pos + 1);
            pos = end + 1;

            var blk = new LoadedBlock();
            blk.rtime    = ReadField(chunk, "rtime");
            blk.duration = ReadField(chunk, "duration");
            blk.x        = ReadField(chunk, "x");
            blk.y        = ReadField(chunk, "y");
            blk.z        = ReadField(chunk, "z");
            blk.gain     = ReadField(chunk, "gain");
            return blk;
        }

        // Read a named float field from a flat JSON object string.
        private static float ReadField(string chunk, string key)
        {
            string search = "\"" + key + "\":";
            int idx = chunk.IndexOf(search, StringComparison.Ordinal);
            if (idx < 0) return 0f;
            idx += search.Length;
            while (idx < chunk.Length && (chunk[idx] == ' ')) idx++;
            int start = idx;
            while (idx < chunk.Length && (char.IsDigit(chunk[idx]) || chunk[idx] == '.' || chunk[idx] == '-')) idx++;
            return float.Parse(chunk.Substring(start, idx - start), CultureInfo.InvariantCulture);
        }

        private static string ReadStringValue(string json, ref int pos)
        {
            // Find the ':' then the opening '"'
            SkipToChar(json, ref pos, ':');
            pos++;
            SkipWhitespace(json, ref pos);
            if (pos < json.Length && json[pos] == '"') pos++;
            int start = pos;
            while (pos < json.Length && json[pos] != '"') pos++;
            string val = json.Substring(start, pos - start);
            pos++; // closing quote
            return val;
        }

        private static float ReadNumberValue(string json, ref int pos)
        {
            SkipToChar(json, ref pos, ':');
            pos++;
            SkipWhitespace(json, ref pos);
            int start = pos;
            while (pos < json.Length && (char.IsDigit(json[pos]) || json[pos] == '.' || json[pos] == '-')) pos++;
            return float.Parse(json.Substring(start, pos - start), CultureInfo.InvariantCulture);
        }

        private static void SkipTo(string json, ref int pos, string token)
        {
            int idx = json.IndexOf(token, pos, StringComparison.Ordinal);
            if (idx < 0) return;
            pos = idx + token.Length;
        }

        private static void SkipToChar(string json, ref int pos, char c)
        {
            while (pos < json.Length && json[pos] != c) pos++;
        }

        private static void SkipWhitespace(string json, ref int pos)
        {
            while (pos < json.Length && (json[pos] == ' ' || json[pos] == '\t' || json[pos] == '\r' || json[pos] == '\n')) pos++;
        }
    }
}
