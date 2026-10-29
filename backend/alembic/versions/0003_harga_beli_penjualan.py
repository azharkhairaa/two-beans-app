"""harga beli per baris penjualan

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-29 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'penjualan_detail',
        sa.Column('harga_beli', sa.Integer(), server_default='0', nullable=False),
    )
    # baris lama diisi harga beli produk saat migration karena HPP waktu itu tidak tersimpan
    op.execute(
        "UPDATE penjualan_detail d SET harga_beli = p.harga_beli FROM produk p "
        "WHERE p.id = d.produk_id"
    )
    # CHECK tidak dideteksi autogenerate, jadi ditulis manual
    op.create_check_constraint(
        op.f('ck_penjualan_detail_harga_beli'), 'penjualan_detail', 'harga_beli >= 0'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f('ck_penjualan_detail_harga_beli'), 'penjualan_detail', type_='check')
    op.drop_column('penjualan_detail', 'harga_beli')
