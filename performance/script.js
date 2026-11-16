import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  thresholds: {
    http_req_duration: ['p(95)<500'], 
    http_req_failed: ['rate<0.01'],  
  },
  scenarios: {
    baseline: {
      executor: 'constant-vus',
      vus: 1,
      duration: '30s',
    },
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  const uniqueRef = `REF-K6-${__VU}-${__ITER}-${Date.now()}`;
  const createPayload = JSON.stringify({
    reference: uniqueRef,
    room_id: 1,
    check_in: '2026-12-01',
    check_out: '2026-12-05',
    guests: 2,
    regular: false,
  });

  const params = {
    headers: { 'Content-Type': 'application/json' },
  };

  const resCreate = http.post(`${BASE_URL}/bookings`, createPayload, params);
  
  const createSuccess = check(resCreate, {
    'create booking status 200/201': (r) => r.status === 200 || r.status === 201,
    'has booking id': (r) => r.json().hasOwnProperty('id') || r.json().hasOwnProperty('booking_id'),
  });

  if (createSuccess) {
    const bookingId = resCreate.json().id || resCreate.json().booking_id || uniqueRef;

    const resGet = http.get(`${BASE_URL}/bookings/${bookingId}`);
    check(resGet, {
      'get booking status 200': (r) => r.status === 200,
    });
  }

  sleep(0.5); 
}