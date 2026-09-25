using UnityEngine;

namespace AmarIbrahim.AdmRecorder
{
    // One stem in the scene: an AudioSource whose position is sampled into blocks while recording.
    [RequireComponent(typeof(AudioSource))]
    public class AudioObject : MonoBehaviour
    {
        [SerializeField]
        [Tooltip("Stem file name written to session.json. Leave blank to use the clip's own file name.")]
        private string stemFileNameOverride = "";

        [SerializeField]
        [Tooltip("World-space meters. A block is emitted whenever the object moves at least this far.")]
        private float positionThreshold = 0.01f;

        public AudioSource AudioSource { get; private set; }
        public string ObjectId { get; private set; }
        public string StemFileName { get; private set; }
        public string TrackName => gameObject.name;

        private SessionController _controller;
        private bool _isRecording;
        private float _blockDurationSeconds;
        private float _intervalAccumulator;
        private Vector3 _lastReportedPosition;
        private float _lastReportTime;

        private void Awake()
        {
            AudioSource = GetComponent<AudioSource>();
            StemFileName = ResolveStemFileName();
        }

        public void Register(SessionController controller, string objectId, float blockDurationSeconds)
        {
            _controller = controller;
            ObjectId = objectId;
            _blockDurationSeconds = blockDurationSeconds;
        }

        public void StartRecording()
        {
            _isRecording = true;
            _intervalAccumulator = 0f;
            _lastReportedPosition = transform.position;
            _lastReportTime = 0f;
        }

        public void StopRecording()
        {
            _isRecording = false;
        }

        public void ForceEmit(float sessionTime)
        {
            TryEmit(sessionTime, forced: true);
        }

        private void Update()
        {
            if (!_isRecording) return;

            _intervalAccumulator += Time.unscaledDeltaTime;

            float sessionTime = (float)(AudioSettings.dspTime - _controller.StartDspTime);

            bool intervalElapsed = _intervalAccumulator >= _blockDurationSeconds;
            bool positionMoved = Vector3.Distance(transform.position, _lastReportedPosition) >= positionThreshold;

            if (intervalElapsed || positionMoved)
            {
                TryEmit(sessionTime, forced: false);
                if (intervalElapsed)
                    _intervalAccumulator -= _blockDurationSeconds;
            }
        }

        private void TryEmit(float sessionTime, bool forced)
        {
            if (!forced && sessionTime <= _lastReportTime) return;

            var report = new PositionReport
            {
                source = this,
                worldPosition = transform.position,
                sessionTime = sessionTime,
                gain = 1.0f
            };

            _controller.ReceivePositionReport(report);
            _lastReportedPosition = transform.position;
            _lastReportTime = sessionTime;
        }

        private string ResolveStemFileName()
        {
            if (!string.IsNullOrEmpty(stemFileNameOverride))
                return stemFileNameOverride;

            var clip = AudioSource.clip;
            if (clip == null)
                return gameObject.name + ".wav";

#if UNITY_EDITOR
            // Takes are recorded in the editor, where the clip's real file name (with extension) is known.
            string assetPath = UnityEditor.AssetDatabase.GetAssetPath(clip);
            if (!string.IsNullOrEmpty(assetPath))
                return System.IO.Path.GetFileName(assetPath);
#endif
            return clip.name + ".wav";
        }
    }
}
