from pawpal_system import Owner, Pet, Task, Scheduler

def main():
    print("🐾 --- PawPal+ Terminal Demo --- 🐾\n")

    # 1. Crear el dueño con su tiempo disponible
    owner = Owner(name="Cinthia", available_time=120)
    
    # 2. Crear las mascotas
    pet1 = Pet(name="Mochi", species="Dog", preferences=["Loves long walks"])
    pet2 = Pet(name="Luna", species="Cat", preferences=["Likes quiet spaces"])
    
    # 3. Registrar las mascotas en el Owner
    owner.add_pet(pet1)
    owner.add_pet(pet2)
    
    # 4. Crear las tareas
    task1 = Task(title="Morning Walk", duration_minutes=30, priority="high", pet_name="Mochi")
    task2 = Task(title="Brush Fur", duration_minutes=15, priority="medium", pet_name="Luna")
    task3 = Task(title="Train commands", duration_minutes=25, priority="high", pet_name="Mochi")
    task4 = Task(title="Quick Feeding", duration_minutes=10, priority="low", pet_name="Luna")
    
    # 5. IMPORTANTE: En lugar de task_pool, asignamos las tareas a los Pets directamente
    # (o al Owner si la función get_all_tasks las junta todas)
    # Probemos agregándolas a las listas internas de cada Pet usando sus métodos:
    try:
        # Si tu clase Pet o Owner tiene un método para guardar tareas individuales:
        # Si da error aquí, es que la lógica colecta las tareas de otra forma.
        if hasattr(pet1, 'tasks'):
            pet1.tasks.append(task1)
            pet1.tasks.append(task3)
            pet2.tasks.append(task2)
            pet2.tasks.append(task4)
    except AttributeError:
        pass
        
    # 6. Crear el planificador asignándole el dueño
    scheduler = Scheduler(owner=owner)
    
    # 7. Construir la agenda del día
    print(f"Generating schedule for {owner.name} (Available Time: {owner.available_time} mins)...")
    scheduler.build_schedule()
    
    # 8. Imprimir el itinerario final
    print("\n🗓️  TODAY'S SCHEDULE:")
    print("=" * 40)
    
    # Verificamos si daily_schedule existe como atributo
    daily_tasks = getattr(scheduler, 'daily_schedule', [])
    
    if not daily_tasks:
        print("No tasks scheduled for today or check your scheduler attribute names.")
    else:
        for item in daily_tasks:
            # Detectar si la IA llamó al atributo 'task' o maneja directo el objeto
            task = getattr(item, 'task', item)
            print(f"⏰ [Scheduled] {task.title} for {task.pet_name}")
            print(f"   ⏱️  Duration: {task.duration_minutes} mins | 🔴 Priority: {task.priority.upper()}")
            print("-" * 40)

    # 9. Imprimir la explicación del plan
    print("\n🧠 SCHEDULER EXPLANATION:")
    print("=" * 40)
    print(scheduler.explain_plan())

if __name__ == "__main__":
    main()