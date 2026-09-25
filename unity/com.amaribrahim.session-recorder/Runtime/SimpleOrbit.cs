using UnityEngine;

namespace AmarIbrahim.AdmRecorder
{
    // Minimal motion source: circles a point so there is movement to record.
    public class SimpleOrbit : MonoBehaviour
    {
        [SerializeField] private Vector3 center = Vector3.zero;
        [SerializeField, Min(0f)] private float radius = 8f;
        [SerializeField] private float degreesPerSecond = 30f;

        [SerializeField, Tooltip("Axis the orbit turns around. Up = a horizontal circle around the listener.")]
        private Vector3 axis = Vector3.up;

        [SerializeField, Tooltip("Starting angle in degrees, so several objects can start spread apart.")]
        private float startAngle = 0f;

        private float _angle;

        private void OnEnable()
        {
            _angle = startAngle;
        }

        private void Update()
        {
            _angle += degreesPerSecond * Time.deltaTime;

            Vector3 n = axis.sqrMagnitude > 0f ? axis.normalized : Vector3.up;
            Vector3 radial = Vector3.Cross(n, Mathf.Abs(n.y) < 0.99f ? Vector3.up : Vector3.right).normalized;
            transform.position = center + Quaternion.AngleAxis(_angle, n) * radial * radius;
        }
    }
}
