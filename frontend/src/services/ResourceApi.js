export class ResourceApi {
  constructor(client, basePath) {
    this.client = client
    this.basePath = basePath
  }

  list(params) {
    return this.client.get(this.basePath, params)
  }

  options(params) {
    return this.client.get(`${this.basePath}/opsi`, params)
  }

  get(id) {
    return this.client.get(`${this.basePath}/${id}`)
  }

  create(body) {
    return this.client.post(this.basePath, body)
  }

  update(id, body) {
    return this.client.put(`${this.basePath}/${id}`, body)
  }

  patch(id, body) {
    return this.client.patch(`${this.basePath}/${id}`, body)
  }

  remove(id) {
    return this.client.delete(`${this.basePath}/${id}`)
  }

  action(id, name, body) {
    return this.client.post(`${this.basePath}/${id}/${name}`, body)
  }
}

export class LokasiApi extends ResourceApi {
  constructor(client) {
    super(client, '/lokasi')
  }
}

export class KategoriApi extends ResourceApi {
  constructor(client) {
    super(client, '/kategori')
  }
}

export class SupplierApi extends ResourceApi {
  constructor(client) {
    super(client, '/supplier')
  }
}

export class CustomerApi extends ResourceApi {
  constructor(client) {
    super(client, '/customer')
  }
}

export class UserApi extends ResourceApi {
  constructor(client) {
    super(client, '/users')
  }

  change(id, body) {
    return this.patch(id, body)
  }

  deliveryman() {
    return this.client.get('/users/deliveryman')
  }
}

export class ProdukApi extends ResourceApi {
  constructor(client) {
    super(client, '/produk')
  }

  kartuStok(id, params) {
    return this.client.get(`/produk/${id}/kartu-stok`, params)
  }
}

export class StokApi {
  constructor(client) {
    this.client = client
  }

  list(params) {
    return this.client.get('/stok', params)
  }

  updateSetting(lokasiId, produkId, body) {
    return this.client.put(`/stok/${lokasiId}/${produkId}`, body)
  }
}

export class TransaksiApi extends ResourceApi {
  constructor(client) {
    super(client, '/transaksi')
  }

  posting(id) {
    return this.action(id, 'posting')
  }
}
