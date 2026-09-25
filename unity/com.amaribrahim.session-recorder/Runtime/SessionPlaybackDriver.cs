using System.Collections;
using System.Collections.Generic;
using UnityEngine;

namespace AmarIbrahim.AdmRecorder
{
    // Drives AudioObject positions from a recorded session during playback.
    // Matches objects by name (GameObject.name == LoadedObject.name), falls back to order.
    public class SessionPlaybackDriver : MonoBehaviour
    {
        [SerializeField]
        [Tooltip("Folder searched by LoadLatestSession, relative to the Unity project folder. Match SessionRecorder's Output Folder.")]
        private string sessionsFolder = "Assets/Sessions";

        private LoadedSession _session;
        private Dictionary<AudioObject, LoadedObject> _bindings;
        private Coroutine _driveCoroutine;
        private double _playbackStartDspTime;

        public bool IsLoaded => _session != null;

        public void LoadSession(string filePath)
        {
            _session = SessionLoader.Load(filePath);
            Debug.Log($"[AdmRecorder] Loaded session '{_session.title}' — {_session.objects.Count} objects, {_session.duration:F2}s");
        }

        // Returns false (and logs a warning) if no recorded session exists yet.
        public bool LoadLatestSession()
        {
            string path = SessionLoader.FindLatestSessionPath(sessionsFolder);
            if (path == null)
            {
                Debug.LogWarning($"[AdmRecorder] No session found in {sessionsFolder}/ — record one first.");
                return false;
            }
            LoadSession(path);
            Debug.Log($"[AdmRecorder] Using session: {path}");
            return true;
        }

        // Bind loaded objects to live AudioObjects and start driving positions.
        // Call after the clips have been scheduled to start at playbackStartDspTime.
        public void StartDriving(IReadOnlyList<AudioObject> audioObjects, double playbackStartDspTime)
        {
            if (_session == null)
            {
                Debug.LogWarning("[AdmRecorder] SessionPlaybackDriver.StartDriving called with no session loaded.");
                return;
            }

            _playbackStartDspTime = playbackStartDspTime;
            _bindings = BindObjects(audioObjects);

            if (_driveCoroutine != null)
                StopCoroutine(_driveCoroutine);
            _driveCoroutine = StartCoroutine(DrivePositions());
        }

        public void StopDriving()
        {
            if (_driveCoroutine != null)
            {
                StopCoroutine(_driveCoroutine);
                _driveCoroutine = null;
            }
        }

        private Dictionary<AudioObject, LoadedObject> BindObjects(IReadOnlyList<AudioObject> audioObjects)
        {
            var bindings = new Dictionary<AudioObject, LoadedObject>();

            // Primary: match by GameObject name.
            foreach (var audioObj in audioObjects)
            {
                foreach (var loadedObj in _session.objects)
                {
                    if (loadedObj.name == audioObj.TrackName)
                    {
                        bindings[audioObj] = loadedObj;
                        break;
                    }
                }
            }

            // Fallback: match by index for anything unmatched.
            int fallbackIdx = 0;
            foreach (var audioObj in audioObjects)
            {
                if (bindings.ContainsKey(audioObj)) continue;
                if (fallbackIdx < _session.objects.Count)
                {
                    bindings[audioObj] = _session.objects[fallbackIdx];
                    Debug.LogWarning($"[AdmRecorder] '{audioObj.TrackName}' matched by index to '{_session.objects[fallbackIdx].name}'");
                }
                fallbackIdx++;
            }

            return bindings;
        }

        private IEnumerator DrivePositions()
        {
            // Track the block cursor per object so we advance linearly.
            var cursors = new Dictionary<AudioObject, int>();
            foreach (var kv in _bindings)
                cursors[kv.Key] = 0;

            while (true)
            {
                float sessionTime = (float)(AudioSettings.dspTime - _playbackStartDspTime);

                foreach (var kv in _bindings)
                {
                    var audioObj = kv.Key;
                    var loadedObj = kv.Value;
                    var blocks = loadedObj.blocks;
                    if (blocks.Count == 0) continue;

                    int idx = cursors[audioObj];

                    // Advance cursor to the block that covers current sessionTime.
                    while (idx < blocks.Count - 1 &&
                           sessionTime >= blocks[idx].rtime + blocks[idx].duration)
                        idx++;

                    cursors[audioObj] = idx;

                    var blk = blocks[idx];

                    // Interpolate between this block and the next if within its duration.
                    Vector3 pos;
                    if (idx < blocks.Count - 1)
                    {
                        var next = blocks[idx + 1];
                        float t = Mathf.Clamp01((sessionTime - blk.rtime) / blk.duration);
                        pos = Vector3.Lerp(
                            new Vector3(blk.x, blk.y, blk.z),
                            new Vector3(next.x, next.y, next.z),
                            t);
                    }
                    else
                    {
                        pos = new Vector3(blk.x, blk.y, blk.z);
                    }

                    audioObj.transform.position = pos;
                }

                yield return null; // advance one frame
            }
        }
    }
}
