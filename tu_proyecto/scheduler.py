import schedule
import time

def job():
    print("Ejecutando tarea programada...")
    # Aquí va la lógica que quieras correr periódicamente,
    # por ejemplo: fetch de Shopify, envío a Zapier, limpieza de DB, etc.

# Programa la tarea cada 10 segundos (puedes cambiar a minutos u horas)
schedule.every(10).seconds.do(job)

# Loop infinito para que siga ejecutando las tareas
while True:
    schedule.run_pending()
    time.sleep(1)
