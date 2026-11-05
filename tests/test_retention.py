from datetime import datetime, timedelta

from backup.retention import Policy, select_to_delete, select_to_keep

BASE = datetime(2026, 1, 31, 3, 0)


def daily_entries(days):
    return [(f"k{i}", BASE - timedelta(days=i)) for i in range(days)]


def test_poucos_backups_mantem_todos():
    entries = daily_entries(5)
    assert select_to_delete(entries, Policy()) == []


def test_limita_quantidade_retida():
    entries = daily_entries(200)
    keep = select_to_keep(entries, Policy(7, 4, 6))
    assert len(keep) <= 7 + 4 + 6
    assert len(keep) >= 7


def test_mantem_os_7_mais_recentes_e_descarta_antigos():
    entries = daily_entries(200)
    keep = select_to_keep(entries, Policy())
    assert {f"k{i}" for i in range(7)} <= keep
    assert "k199" not in keep


def test_mantem_um_por_mes_ao_longo_do_tempo():
    entries = daily_entries(200)
    keep = select_to_keep(entries, Policy(daily=1, weekly=0, monthly=6))
    months = {(ts.year, ts.month) for k, ts in entries if k in keep}
    assert len(months) == 6


def test_varios_backups_no_mesmo_dia_fica_o_mais_novo():
    entries = [("novo", BASE), ("velho", BASE - timedelta(hours=2))]
    assert select_to_delete(entries, Policy()) == ["velho"]
