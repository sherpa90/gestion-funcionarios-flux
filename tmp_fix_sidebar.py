path = 'templates/base.html'
with open(path, 'r') as f:
    content = f.read()

old_block = '''                {% if user.role == 'ADMIN' or user.role == 'SECRETARIA' %}
                {% if user.role != 'SECRETARIA' %}
                <a href="{% url 'inventario_equipos' %}" class="sidebar-link flex items-center px-3 py-2 rounded-lg">
                    <i class="fa-solid fa-boxes-stacked fa-fw mr-3 text-slate-400 text-xs"></i><span>Inventario</span>
                </a>
                <a href="{% url 'lista_equipos' %}" class="sidebar-link flex items-center px-3 py-2 rounded-lg">
                    <i class="fa-solid fa-laptop-file fa-fw mr-3 text-slate-400 text-xs"></i><span>Equipos / Préstamos</span>
                </a>
                <a href="{% url 'gestion_fallas' %}" class="sidebar-link flex items-center justify-between px-3 py-2 rounded-lg">
                    <div class="flex items-center">
                        <i class="fa-solid fa-clipboard-list fa-fw mr-3 text-slate-400 text-xs"></i><span>Bitácora & Tickets</span>
                    </div>
                    {% if pending_failures_count > 0 %}
                    <span class="flex items-center justify-center w-4 h-4 text-[9px] font-bold bg-rose-600 text-white rounded-full">
                        {{ pending_failures_count }}
                    </span>
                    {% endif %}
                </a>
                {% endif %}'''

new_block = '''                {% if user.role == 'ADMIN' or user.role == 'SECRETARIA' %}
                {% if user.role != 'SECRETARIA' %}
                <!-- Equipamiento -->
                <div class="pt-3 pb-1">
                    <p class="px-3 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Equipamiento</p>
                </div>
                <a href="{% url 'inventario_equipos' %}" class="sidebar-link flex items-center px-3 py-2 rounded-lg">
                    <i class="fa-solid fa-boxes-stacked fa-fw mr-3 text-slate-400 text-xs"></i><span>Inventario</span>
                </a>
                <a href="{% url 'lista_equipos' %}" class="sidebar-link flex items-center px-3 py-2 rounded-lg">
                    <i class="fa-solid fa-laptop-file fa-fw mr-3 text-slate-400 text-xs"></i><span>Equipos / Préstamos</span>
                </a>
                <a href="{% url 'gestion_fallas' %}" class="sidebar-link flex items-center justify-between px-3 py-2 rounded-lg">
                    <div class="flex items-center">
                        <i class="fa-solid fa-clipboard-list fa-fw mr-3 text-slate-400 text-xs"></i><span>Bitácora & Tickets</span>
                    </div>
                    {% if pending_failures_count > 0 %}
                    <span class="flex items-center justify-center w-4 h-4 text-[9px] font-bold bg-rose-600 text-white rounded-full">
                        {{ pending_failures_count }}
                    </span>
                    {% endif %}
                </a>
                {% endif %}'''

if old_block in content:
    content = content.replace(old_block, new_block)
    with open(path, 'w') as f:
        f.write(content)
    print('Updated successfully')
else:
    print('Block not found')
