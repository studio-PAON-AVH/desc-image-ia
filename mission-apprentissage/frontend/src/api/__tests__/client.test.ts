import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import apiClient from '../client';

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('apiClient interceptor', () => {
  it('retourne la réponse normalement si pas de 401', async () => {
    server.use(
      http.get('http://localhost:8000/api/epub', () =>
        HttpResponse.json({ epubs: [] }, { status: 200 })
      )
    );
    const res = await apiClient.get('/api/epub');
    expect(res.status).toBe(200);
    expect(res.data).toEqual({ epubs: [] });
  });

  it('tente un refresh et rejoue la requête originale si 401', async () => {
    let refreshCalled = false;
    let callCount = 0;

    server.use(
      http.get('http://localhost:8000/api/epub', () => {
        callCount++;
        if (callCount === 1) {
          return HttpResponse.json({ detail: 'Unauthorized' }, { status: 401 });
        }
        return HttpResponse.json({ epubs: ['test.epub'] }, { status: 200 });
      }),
      http.post('http://localhost:8000/api/auth/refresh', () => {
        refreshCalled = true;
        return HttpResponse.json({}, { status: 200 });
      })
    );

    const res = await apiClient.get('/api/epub');
    expect(refreshCalled).toBe(true);
    expect(res.status).toBe(200);
    expect(res.data).toEqual({ epubs: ['test.epub'] });
  });

  it('rejette si le refresh échoue', async () => {
    server.use(
      http.get('http://localhost:8000/api/epub', () =>
        HttpResponse.json({ detail: 'Unauthorized' }, { status: 401 })
      ),
      http.post('http://localhost:8000/api/auth/refresh', () =>
        HttpResponse.json({ detail: 'Refresh invalid' }, { status: 401 })
      )
    );
    await expect(apiClient.get('/api/epub')).rejects.toThrow();
  });

  it("ne tente pas de refresh sur l'endpoint login", async () => {
    let refreshCalled = false;
    server.use(
      http.post('http://localhost:8000/api/auth/login', () =>
        HttpResponse.json({ detail: 'Bad credentials' }, { status: 401 })
      ),
      http.post('http://localhost:8000/api/auth/refresh', () => {
        refreshCalled = true;
        return HttpResponse.json({}, { status: 200 });
      })
    );
    await expect(apiClient.post('/api/auth/login', {})).rejects.toThrow();
    expect(refreshCalled).toBe(false);
  });

  it("ne tente pas de refresh sur l'endpoint refresh lui-même", async () => {
    let refreshCount = 0;
    server.use(
      http.post('http://localhost:8000/api/auth/refresh', () => {
        refreshCount++;
        return HttpResponse.json({ detail: 'Invalid' }, { status: 401 });
      })
    );
    await expect(apiClient.post('/api/auth/refresh')).rejects.toThrow();
    expect(refreshCount).toBe(1);
  });
});
