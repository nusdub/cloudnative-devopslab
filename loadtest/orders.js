import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 20 },
    { duration: '1m', target: 50 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<300'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  const payload = JSON.stringify({ item: 'sre-book', quantity: 1, region: 'cn-east' });
  const response = http.post(`${BASE_URL}/api/orders`, payload, {
    headers: { 'Content-Type': 'application/json' },
  });
  check(response, {
    'created': (r) => r.status === 201,
    'latency under 300ms': (r) => r.timings.duration < 300,
  });
  sleep(1);
}
