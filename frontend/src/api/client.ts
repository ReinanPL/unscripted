/**
 * Cliente HTTP base do frontend. Todas as chamadas passam por aqui.
 * O backend é alcançado por paths relativos — o proxy do Vite (em dev)
 * e o reverse proxy de produção encaminham para o backend real.
 */

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(message: string, status: number, body: unknown = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

export class NetworkError extends Error {
  constructor(message = "Network error") {
    super(message);
    this.name = "NetworkError";
  }
}

export interface RequestOptions extends RequestInit {
  expect?: "json" | "raw";
}

export async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { expect = "json", headers, ...rest } = options;

  let response: Response;
  try {
    response = await fetch(path, {
      headers: {
        Accept: "application/json",
        ...headers,
      },
      ...rest,
    });
  } catch (cause) {
    throw new NetworkError(
      cause instanceof Error ? cause.message : "Network error",
    );
  }

  if (!response.ok) {
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      // body fica null
    }
    throw new ApiError(
      `Request to ${path} failed with status ${response.status}`,
      response.status,
      body,
    );
  }

  if (expect === "raw") {
    return response as unknown as T;
  }
  return (await response.json()) as T;
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

export function isNotFound(error: unknown): boolean {
  return isApiError(error) && error.status === 404;
}

export function isNetworkError(error: unknown): error is NetworkError {
  return error instanceof NetworkError;
}
