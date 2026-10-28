export class ApiError extends Error {
  // status 0 berarti request tidak sampai ke server
  constructor(status, message, errors = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.errors = errors
  }
}

export class ApiClient {
  static UNSAFE_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])
  static FALLBACK_MESSAGES = {
    0: 'Tidak bisa terhubung ke server. Periksa koneksi lalu coba lagi.',
    429: 'Terlalu banyak percobaan. Coba lagi nanti.',
    500: 'Terjadi error di server. Coba lagi beberapa saat lagi.',
  }

  constructor(baseUrl = '/api') {
    this.baseUrl = baseUrl
    // diisi saat aplikasi dipasang: token CSRF dari store auth dan penanganan sesi berakhir
    this.csrfTokenProvider = () => null
    this.onUnauthorized = null
  }

  get(path, params) {
    return this.request('GET', path, { params })
  }

  post(path, body) {
    return this.request('POST', path, { body })
  }

  put(path, body) {
    return this.request('PUT', path, { body })
  }

  patch(path, body) {
    return this.request('PATCH', path, { body })
  }

  delete(path) {
    return this.request('DELETE', path)
  }

  async request(method, path, { body, params } = {}) {
    const url = new URL(this.baseUrl + path, window.location.origin)
    for (const [key, value] of Object.entries(params || {})) {
      if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, value)
    }
    let response
    try {
      response = await fetch(url, {
        method,
        headers: this.headers(method, body),
        body: body === undefined ? undefined : JSON.stringify(body),
        credentials: 'same-origin',
      })
    } catch {
      throw new ApiError(0, ApiClient.FALLBACK_MESSAGES[0])
    }
    const data = await this.parse(response)
    if (!response.ok) {
      const error = this.toError(response.status, data)
      if (error.status === 401 && this.onUnauthorized) this.onUnauthorized(path)
      throw error
    }
    return data
  }

  headers(method, body) {
    const headers = { Accept: 'application/json' }
    if (body !== undefined) headers['Content-Type'] = 'application/json'
    // token CSRF hanya disimpan di memori dan dikirim untuk method pengubah data
    const token = this.csrfTokenProvider()
    if (ApiClient.UNSAFE_METHODS.has(method) && token) headers['X-CSRF-Token'] = token
    return headers
  }

  async parse(response) {
    const text = await response.text()
    try {
      return text ? JSON.parse(text) : null
    } catch {
      return null
    }
  }

  toError(status, data) {
    const fallback = ApiClient.FALLBACK_MESSAGES[status >= 500 ? 500 : status] || `Permintaan gagal (${status})`
    const message = typeof data?.detail === 'string' ? data.detail : fallback
    return new ApiError(status, message, data?.errors || {})
  }
}
