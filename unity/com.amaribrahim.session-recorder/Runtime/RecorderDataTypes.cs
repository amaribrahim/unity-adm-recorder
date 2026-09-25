using UnityEngine;

namespace AmarIbrahim.AdmRecorder
{
    public struct BlockData
    {
        public float rtime;
        public float duration;
        public float x;
        public float y;
        public float z;
        public float gain;
    }

    public struct PositionReport
    {
        public AudioObject source;
        public Vector3 worldPosition;
        public float sessionTime;
        public float gain;
    }
}
