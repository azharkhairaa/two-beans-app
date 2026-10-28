export class AuthApi {
  constructor(client) {
    this.client = client
  }

  register(data) {
    return this.client.post('/auth/register', data)
  }

  login(email, password) {
    return this.client.post('/auth/login', { email, password })
  }

  logout() {
    return this.client.post('/auth/logout')
  }

  me() {
    return this.client.get('/auth/me')
  }
}
