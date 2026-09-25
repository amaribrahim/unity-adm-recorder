using System.Collections.Generic;
using UnityEngine;

namespace AmarIbrahim.AdmRecorder
{
    // Runs a take: starts every AudioObject's clip on the same DSP tick, then either records
    // their movement to session.json or replays the newest recorded session.
    // Prototype transport: a take always runs for the length of the longest stem.
    public class SessionController : MonoBehaviour
    {
        public enum OnPlayAction { Record, PlayLatestSession, Nothing }

        [SerializeField]
        [Tooltip("What happens when you press Play. Nothing = call StartRecording / PlayLatestSession from your own scripts.")]
        private OnPlayAction onPlay = OnPlayAction.Record;

        [SerializeField] private SessionRecorder sessionRecorder;
        [SerializeField] private SessionPlaybackDriver playbackDriver;

        [SerializeField]
        [Tooltip("Block length in samples at 48 kHz for objects that stay still (2400 = 50 ms). Moving objects emit a block every frame regardless.")]
        private int blockDurationSamples = 2400;

        [SerializeField]
        [Tooltip("Scene bounding sphere radius in meters. Positions are divided by this to reach ADM's -1..1 range.")]
        private float sceneRadius = 20f;

        [SerializeField]
        [Tooltip("Leave empty to use every AudioObject under this GameObject, in hierarchy order.")]
        private List<AudioObject> objects = new List<AudioObject>();

        private const double ScheduleLeadSeconds = 0.1;

        public IReadOnlyList<AudioObject> Objects => objects;
        public double StartDspTime { get; private set; }
        public bool IsRecording => _isRecording;

        private bool _isRecording;
        private bool _isPlaying;
        private float _sessionDuration;

        private void Awake()
        {
            if (objects == null || objects.Count == 0)
                objects = new List<AudioObject>(GetComponentsInChildren<AudioObject>());

            float blockSecs = blockDurationSamples / 48000f;
            for (int i = 0; i < objects.Count; i++)
                objects[i].Register(this, $"obj_{(i + 1):D4}", blockSecs);
        }

        private void Start()
        {
            _sessionDuration = ComputeSessionDuration();

            switch (onPlay)
            {
                case OnPlayAction.Record: StartRecording(); break;
                case OnPlayAction.PlayLatestSession: PlayLatestSession(); break;
            }
        }

        private void Update()
        {
            if (!_isPlaying) return;
            if (AudioSettings.dspTime < StartDspTime + _sessionDuration) return;

            if (_isRecording) StopRecording();
            else StopPlayback();
        }

        // Starts all stems in sync and records every AudioObject until the longest stem ends.
        public void StartRecording()
        {
            if (_isPlaying) return;
            if (sessionRecorder == null)
            {
                Debug.LogError("[AdmRecorder] SessionController needs a SessionRecorder assigned to record.");
                return;
            }
            if (objects.Count == 0)
            {
                Debug.LogError("[AdmRecorder] No AudioObjects found under the SessionController.");
                return;
            }

            sessionRecorder.BeginRecording(objects, _sessionDuration, blockDurationSamples, sceneRadius);
            ScheduleClips();

            _isRecording = true;
            foreach (var obj in objects)
            {
                obj.StartRecording();
                obj.ForceEmit(0f);
            }

            Debug.Log($"[AdmRecorder] Recording {objects.Count} objects for {_sessionDuration:F1}s");
        }

        // Ends the take (automatically at the end of the stems, or early if called) and writes session.json.
        public void StopRecording()
        {
            if (!_isRecording) return;
            _isRecording = false;

            foreach (var obj in objects)
                obj.StopRecording();

            sessionRecorder.StopRecording();
            StopPlayback();
        }

        // Plays the stems while the newest recorded session drives the objects' positions.
        public void PlayLatestSession()
        {
            if (_isPlaying) return;
            if (playbackDriver == null)
            {
                Debug.LogError("[AdmRecorder] SessionController needs a SessionPlaybackDriver assigned to play back.");
                return;
            }
            if (!playbackDriver.LoadLatestSession()) return;

            ScheduleClips();
            playbackDriver.StartDriving(objects, StartDspTime);
        }

        public void StopPlayback()
        {
            _isPlaying = false;
            if (playbackDriver != null)
                playbackDriver.StopDriving();
            foreach (var obj in objects)
                obj.AudioSource.Stop();
        }

        public void ReceivePositionReport(PositionReport report)
        {
            sessionRecorder.AccumulateBlock(report);
        }

        private void ScheduleClips()
        {
            StartDspTime = AudioSettings.dspTime + ScheduleLeadSeconds;
            foreach (var obj in objects)
            {
                if (obj.AudioSource.clip != null)
                    obj.AudioSource.PlayScheduled(StartDspTime);
                else
                    Debug.LogWarning($"[AdmRecorder] AudioObject '{obj.name}' has no clip assigned.");
            }
            _isPlaying = true;
        }

        private float ComputeSessionDuration()
        {
            float max = 0f;
            foreach (var obj in objects)
            {
                if (obj.AudioSource.clip != null)
                    max = Mathf.Max(max, obj.AudioSource.clip.length);
            }
            return max;
        }
    }
}
