"""F11 -- aislamiento entre sesiones: la idempotencia se llavea por sesion + usuario + tool + args."""
import idempotency


def test_la_clave_de_idempotencia_separa_sesiones_y_usuarios():
    args = {"query": "x"}
    a = idempotency.make_key("180:room-1", 180, "OpenSupportTicketTool", args)
    assert a != idempotency.make_key("181:room-1", 181, "OpenSupportTicketTool", args)
    assert a != idempotency.make_key("180:room-2", 180, "OpenSupportTicketTool", args)
    assert a != idempotency.make_key("180:room-1", 180, "OtraTool", args)
    assert a != idempotency.make_key("180:room-1", 180, "OpenSupportTicketTool", {"query": "y"})
    assert a == idempotency.make_key("180:room-1", 180, "OpenSupportTicketTool", {"query": "x"})


def test_la_clave_no_depende_del_orden_de_los_argumentos():
    assert idempotency.make_key("s", 1, "T", {"a": 1, "b": 2}) == idempotency.make_key("s", 1, "T", {"b": 2, "a": 1})


def test_los_ids_de_correlacion_invalidos_se_descartan():
    import observability_logging as obs

    for bad in ("con espacios y basura", "x" * 100, "a;b;c;d;e;f;g;h", None):
        assert obs.valid_id(bad) is None
