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

export class PengirimanApi extends ResourceApi {
  constructor(client) {
    super(client, '/pengiriman')
  }

  kirim(id, body) {
    return this.action(id, 'kirim', body)
  }

  terima(id, body) {
    return this.action(id, 'terima', body)
  }
}

export class PermintaanApi extends ResourceApi {
  constructor(client) {
    super(client, '/permintaan')
  }

  batal(id) {
    return this.action(id, 'batal')
  }

  setujui(id, body) {
    return this.action(id, 'setujui', body)
  }

  tolak(id, body) {
    return this.action(id, 'tolak', body)
  }
}

export class PembelianApi extends ResourceApi {
  constructor(client) {
    super(client, '/pembelian')
  }

  pesan(id) {
    return this.action(id, 'pesan')
  }

  terima(id, body) {
    return this.action(id, 'terima', body)
  }

  batal(id) {
    return this.action(id, 'batal')
  }
}

export class PenjualanApi extends ResourceApi {
  constructor(client) {
    super(client, '/penjualan')
  }

  posting(id) {
    return this.action(id, 'posting')
  }
}

export class DashboardApi {
  constructor(client) {
    this.client = client
  }

  summary() {
    return this.client.get('/dashboard')
  }

  monitoring(params) {
    return this.client.get('/dashboard/monitoring', params)
  }

  tren(params) {
    return this.client.get('/dashboard/tren', params)
  }
}
