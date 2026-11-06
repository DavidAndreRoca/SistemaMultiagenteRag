import httpx


async def test_salud_informa_degradado_si_la_base_no_responde(
    cliente_sin_bd: httpx.AsyncClient,
) -> None:
    respuesta = await cliente_sin_bd.get("/salud")
    cuerpo = respuesta.json()
    assert respuesta.status_code == 503
    assert cuerpo["estado"] == "degradado"
    assert cuerpo["base_de_datos"] is False
    assert cuerpo["extension_vector"] is None
    # Ni la URL de conexión ni credenciales salen en la respuesta.
    assert "127.0.0.1" not in respuesta.text
