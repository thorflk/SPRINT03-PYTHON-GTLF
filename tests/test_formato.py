from chargegrid.formato import br


def test_br_usa_virgula_decimal_e_ponto_de_milhar():
    assert br(1234.5) == "1.234,50"
    assert br(0.85) == "0,85"
    assert br(24, 0) == "24"
