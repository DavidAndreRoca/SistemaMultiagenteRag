# Servidor de desarrollo en Oracle (T01)

Entorno compartido de desarrollo en la misma arquitectura (ARM) que producción, en la cuenta de Oracle de David (D-03). Ambos integrantes trabajan con Claude Code en usuarios Linux separados.

> **Estado:** este documento es la guía de operación. La instancia no pudo crearse desde la sesión que implementó la Fase 1 (requiere acceso a la cuenta de Oracle). Los pasos 1 a 4 los ejecuta una persona y se marcan en `docs/ESTADO_DESARROLLO.md` cuando se verifiquen con los scripts de este repositorio.

## 1. Crear la instancia (en la consola de Oracle)

1. Instancia de computación con forma **Ampere A1 (ARM)**, con el máximo de recursos del cupo Always Free de la cuenta y un volumen de arranque suficiente para modelos, imágenes y datos de prueba. Consulte los límites vigentes en la página de Always Free de Oracle antes de elegir.
2. Imagen Ubuntu LTS para ARM.
3. Subred pública con la lista de seguridad abierta **solo al puerto 22 (SSH)**.
4. Cargue la llave pública de David al crear la instancia.
5. No cree cuentas gratuitas adicionales de Oracle (R-05): una cuenta por persona.

## 2. Endurecer el acceso

En `/etc/ssh/sshd_config.d/99-proyecto.conf`:

```text
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
PubkeyAuthentication yes
```

Luego `sudo systemctl restart ssh`. Compruebe también que el cortafuegos del sistema (`sudo iptables -L` o `ufw status`) no abre otros puertos de entrada.

## 3. Usuarios por integrante

```bash
sudo adduser --disabled-password --gecos "" david
sudo adduser --disabled-password --gecos "" angel
sudo usermod -aG docker david && sudo usermod -aG docker angel   # tras instalar Docker
sudo -u angel mkdir -p /home/angel/.ssh && sudo -u angel chmod 700 /home/angel/.ssh
# pegar la llave pública de cada integrante en /home/<usuario>/.ssh/authorized_keys (modo 600)
```

Cada integrante trabaja en su propia copia del repositorio dentro de su carpeta de usuario.

## 4. Instalar herramientas

* Docker Engine y el complemento Compose, siguiendo la guía oficial de instalación para Ubuntu.
* Git, Python 3.12 y Node.js en versión de soporte prolongado.
* Claude Code, siguiendo su guía oficial de instalación.

Verificación (ejecutar como cada integrante):

```bash
bash scripts/verificar-herramientas.sh
```

Verificación de imágenes con soporte ARM (puede ejecutarse desde cualquier máquina con Docker):

```bash
bash scripts/verificar-imagenes-arm.sh
```

Resultado de la última ejecución (6 de noviembre de 2026): `pgvector/pgvector:pg16`, `python:3.12-slim`, `node:22-slim` y `grobid/grobid:0.9.1-crf` tienen arm64. Las etiquetas 0.8.x de GROBID no. Ver `docs/decisiones/T01-grobid-arm64.md`.

## 5. Servicios compartidos y bases por integrante

* **Proyecto de Compose `compartido`** (GROBID y servicio de modelos, T08): se ejecuta una sola vez para ambos integrantes, para no duplicar memoria (R-02). Lo levanta uno de los dos, desde su copia del repositorio:

```bash
cp compartido/.env.example compartido/.env
```

```bash
docker compose -f compartido/docker-compose.yml --profile descarga run --rm --build descargar_modelos
```

```bash
docker compose -f compartido/docker-compose.yml up -d --wait
```

  La descarga baja unos 4,6 GB al volumen `sma_modelos`, verifica las huellas y solo hace falta una vez. Luego compruebe `curl http://127.0.0.1:8001/salud` (modelos, revisiones y memoria) y `curl http://127.0.0.1:8070/api/isalive` (GROBID). Para medir la memoria del conjunto: `docker stats --no-stream` y `free -m` (el criterio de T08 exige que no haya intercambio a disco). Las pruebas con los pesos reales: `docker compose -f compartido/docker-compose.yml --profile pruebas run --rm --build pruebas_modelos`. Detalle en `docs/decisiones/T08-servicios-compartidos.md`.
* **Proyecto de Compose por integrante** (base de datos y API de este repositorio): cada uno define en su `.env` un `COMPOSE_PROJECT_NAME` propio (`sma_david`, `sma_angel`) y puertos distintos (`PUERTO_BD`, `PUERTO_API`). El `docker-compose.yml` de este repositorio publica los puertos solo en `127.0.0.1`; para ver la API desde su equipo use un túnel SSH:

```bash
ssh -L 8000:127.0.0.1:8000 david@<ip-del-servidor>
```

## 6. Evitar que la instancia quede inactiva

Oracle puede reclamar las instancias Always Free con uso muy bajo durante un periodo prolongado, y suspender cuentas inactivas (riesgo R-04; la hoja de ruta cita las preguntas frecuentes de Always Free de Oracle). Los criterios exactos de uso mínimo y plazos deben confirmarse en la documentación vigente de Oracle, porque cambian. Medidas del proyecto:

* Usar la instancia regularmente para desarrollo.
* Revisar en la consola de Oracle los avisos de inactividad.
* Si Oracle publica un umbral de uso, programar una tarea ligera periódica solo si hace falta y está permitido por sus términos.

## 7. Criterios de aceptación de T01 (lista de comprobación)

| Criterio | Cómo se comprueba | Estado |
| --- | --- | --- |
| Ambos integrantes entran por SSH con su usuario | `ssh usuario@servidor` con llave | Pendiente (requiere la instancia) |
| Rechazo de acceso con contraseña | `ssh -o PubkeyAuthentication=no usuario@servidor` debe fallar | Pendiente |
| `docker run` de PostgreSQL con pgvector funciona en ARM | `scripts/verificar-herramientas.sh` | Pendiente |
| Claude Code se inicia en la carpeta de cada usuario | `claude --version` y arranque en la carpeta | Pendiente |
| Imágenes previstas existen para ARM | `scripts/verificar-imagenes-arm.sh` | **Verificado** (con la salvedad de GROBID) |
| (De T08) Servicios compartidos sanos y sin intercambio a disco con dos bases | `compartido/docker-compose.yml` (`up`, `pruebas_modelos`), `docker stats` y `free -m` | Pendiente: instancia en trámite con Oracle (incidente 261107-001540); ver `docs/decisiones/T08-emulacion-arm64.md` |
