const request = require('supertest');
const app = require('../index'); // Import the real app

describe('Timestamp API', () => {
  it('should handle a valid date string', async () => {
    const res = await request(app).get('/api/2015-12-25');
    expect(res.statusCode).toEqual(200);
    expect(res.body).toEqual({
      unix: 1451001600000,
      utc: 'Fri, 25 Dec 2015 00:00:00 GMT',
    });
  });

  it('should handle a valid unix timestamp', async () => {
    const res = await request(app).get('/api/1451001600000');
    expect(res.statusCode).toEqual(200);
    expect(res.body).toEqual({
      unix: 1451001600000,
      utc: 'Fri, 25 Dec 2015 00:00:00 GMT',
    });
  });

  it('should return an error for an invalid date', async () => {
    const res = await request(app).get('/api/this-is-not-a-date');
    expect(res.statusCode).toEqual(200); // The API returns 200 OK for this error case
    expect(res.body).toEqual({ error: 'Invalid Date' });
  });

  it('should handle an empty date parameter and return the current time', async () => {
    const res = await request(app).get('/api/');
    const now = Date.now();
    expect(res.statusCode).toEqual(200);
    // Check if the returned unix time is close to the current time
    expect(res.body.unix).toBeCloseTo(now, -2); // within ~100ms
  });
});
