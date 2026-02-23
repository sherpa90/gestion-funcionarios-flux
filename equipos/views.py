from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from django.conf import settings
from weasyprint import HTML
from .models import Equipo, PrestamoEquipo, FallaEquipo
from users.models import CustomUser
from datetime import datetime


@login_required
@login_required
def lista_equipos(request):
    """Lista todos los equipos (solo administradores)"""
    if request.user.role not in ('ADMIN', 'SECRETARIA'):
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('dashboard')

    equipos_base = Equipo.objects.all()
    
    # Resumen para el dashboard
    stats = {
        'total': equipos_base.count(),
        'disponibles': equipos_base.filter(estado='DISPONIBLE').count(),
        'asignados': equipos_base.filter(estado='ASIGNADO').count(),
        'reparacion': equipos_base.filter(estado='EN_REPARACION').count(),
    }

    # Filtros
    tipo = request.GET.get('tipo')
    estado = request.GET.get('estado')
    funcionario_id = request.GET.get('funcionario_id')

    equipos = equipos_base
    if tipo:
        equipos = equipos.filter(tipo=tipo)
    if estado:
        equipos = equipos.filter(estado=estado)

    # Lista de funcionarios para el selector
    funcionarios = CustomUser.objects.all().order_by('first_name', 'last_name')

    selected_funcionario = None
    if funcionario_id:
        selected_funcionario = get_object_or_404(CustomUser, id=funcionario_id)
        # Si se seleccionó un funcionario, filtramos los equipos asignados a él
        equipos_vía_prestamo = PrestamoEquipo.objects.filter(funcionario=selected_funcionario, activo=True).values_list('equipo_id', flat=True)
        equipos = equipos.filter(id__in=equipos_vía_prestamo)

    # Sanitizar y preparar datos
    for equipo in equipos:
        # Sanitizar campos de texto
        for campo in ['numero_serie', 'numero_inventario', 'marca', 'modelo']:
            valor = getattr(equipo, campo, '')
            if valor:
                valor_limpio = valor.replace('{{', '').replace('}}', '').replace('{%', '').replace('%}', '').strip()
                setattr(equipo, campo, valor_limpio)
        
        # Obtener préstamo activo
        equipo.prestamo_activo = equipo.prestamos.filter(activo=True).select_related('funcionario').first()

    # Si hay un funcionario seleccionado, solo mostramos sus equipos en la sección de asignados
    asignados_por_funcionario = []
    if selected_funcionario:
        asignados_por_funcionario = [{
            'funcionario': selected_funcionario,
            'equipos': equipos
        }]
    
    # El inventario (que no tiene asignado activo o está disponible/taller)
    # Si filtramos por funcionario, el inventario general no debería verse o debería estar separado.
    # El usuario dijo: "se desplegan los equipos que tiene en su poder"
    # Mantendremos no_asignados para mostrar el inventario general si no se filtra por funcionario, 
    # o como sección aparte.
    
    no_asignados = equipos_base.exclude(prestamos__activo=True)
    if tipo:
        no_asignados = no_asignados.filter(tipo=tipo)
    if estado:
        no_asignados = no_asignados.filter(estado=estado)

    context = {
        'asignados_por_funcionario': asignados_por_funcionario,
        'no_asignados': no_asignados,
        'tipos': Equipo.TIPO_CHOICES,
        'estados': Equipo.ESTADO_CHOICES,
        'funcionarios': funcionarios,
        'selected_funcionario': selected_funcionario,
        'stats': stats,
        'filtros_activos': bool(tipo or estado or funcionario_id),
    }
    return render(request, 'equipos/lista_equipos.html', context)


@login_required
def crear_equipo(request):
    """Crear nuevo equipo (solo administradores)"""
    if request.user.role not in ('ADMIN', 'SECRETARIA'):
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('dashboard')

    if request.method == 'POST':
        try:
            # Determinar estado inicial
            funcionario_id = request.POST.get('funcionario')
            estado_inicial = 'ASIGNADO' if funcionario_id else 'DISPONIBLE'

            equipo = Equipo.objects.create(
                tipo=request.POST.get('tipo'),
                marca=request.POST.get('marca'),
                modelo=request.POST.get('modelo'),
                numero_serie=request.POST.get('numero_serie', '').upper(),
                numero_inventario=request.POST.get('numero_inventario', '').upper(),
                observaciones=request.POST.get('observaciones', ''),
                estado=estado_inicial,
                fecha_adquisicion=request.POST.get('fecha_adquisicion') or None,
                creado_por=request.user
            )

            # Vincular a funcionario si se especificó
            if funcionario_id:
                funcionario = CustomUser.objects.get(id=funcionario_id)
                PrestamoEquipo.objects.create(
                    equipo=equipo,
                    funcionario=funcionario,
                    asignado_por=request.user,
                    activo=True
                )

            messages.success(request, f'Equipo {equipo} creado exitosamente.')
            return redirect('lista_equipos')
        except Exception as e:
            messages.error(request, f'Error al crear equipo: {str(e)}')

    funcionarios = CustomUser.objects.filter(is_active=True).order_by('last_name')

    context = {
        'tipos': Equipo.TIPO_CHOICES,
        'estados': Equipo.ESTADO_CHOICES,
        'funcionarios': funcionarios,
    }
    return render(request, 'equipos/crear_equipo.html', context)


@login_required
def editar_equipo(request, equipo_id):
    """Editar equipo (solo administradores)"""
    if request.user.role not in ('ADMIN', 'SECRETARIA'):
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('dashboard')

    # Validar que el ID sea un número entero válido
    try:
        equipo_id = int(equipo_id)
    except (ValueError, TypeError):
        messages.error(request, 'ID de equipo inválido.')
        return redirect('lista_equipos')

    equipo = get_object_or_404(Equipo, id=equipo_id)

    if request.method == 'POST':
        equipo.tipo = request.POST.get('tipo')
        equipo.marca = request.POST.get('marca')
        equipo.modelo = request.POST.get('modelo')
        equipo.numero_serie = request.POST.get('numero_serie', '').upper()
        equipo.numero_inventario = request.POST.get('numero_inventario', '').upper()
        equipo.observaciones = request.POST.get('observaciones', '')
        equipo.estado = request.POST.get('estado')
        equipo.fecha_adquisicion = request.POST.get('fecha_adquisicion') or None
        equipo.save()

        # Manejo de vinculación/desvinculación
        funcionario_id = request.POST.get('funcionario')
        prestamo_actual = equipo.prestamos.filter(activo=True).first()

        if funcionario_id:
            # Si se seleccionó un funcionario
            if not prestamo_actual or prestamo_actual.funcionario.id != int(funcionario_id):
                # Si no había préstamo o es un funcionario distinto
                if prestamo_actual:
                    prestamo_actual.activo = False
                    prestamo_actual.fecha_devolucion = timezone.now().date()
                    prestamo_actual.save()
                
                # Crear nuevo préstamo
                PrestamoEquipo.objects.create(
                    equipo=equipo,
                    funcionario_id=funcionario_id,
                    asignado_por=request.user,
                    activo=True
                )
                equipo.estado = 'ASIGNADO'
                equipo.save()
        else:
            # Si no se seleccionó funcionario y había uno vinculado
            if prestamo_actual:
                prestamo_actual.activo = False
                prestamo_actual.fecha_devolucion = timezone.now().date()
                prestamo_actual.save()
                
                # Si el usuario no cambió el estado manualmente a otra cosa, ponerlo como Disponible
                if equipo.estado == 'ASIGNADO':
                    equipo.estado = 'DISPONIBLE'
                    equipo.save()

        messages.success(request, 'Equipo actualizado exitosamente.')
        return redirect('lista_equipos')

    prestamo_actual = equipo.prestamos.filter(activo=True).first()
    funcionarios = CustomUser.objects.filter(is_active=True).order_by('last_name')

    context = {
        'equipo': equipo,
        'tipos': Equipo.TIPO_CHOICES,
        'estados': Equipo.ESTADO_CHOICES,
        'funcionarios': funcionarios,
        'prestamo_actual': prestamo_actual,
    }
    return render(request, 'equipos/editar_equipo.html', context)


@login_required
def eliminar_equipo(request, equipo_id):
    """Eliminar equipo (solo administradores)"""
    if request.user.role != 'ADMIN':
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('dashboard')

    equipo = get_object_or_404(Equipo, id=equipo_id)

    if request.method == 'POST':
        equipo.delete()
        messages.success(request, 'Equipo eliminado exitosamente.')
        return redirect('lista_equipos')

    context = {'equipo': equipo}
    return render(request, 'equipos/eliminar_equipo.html', context)


@login_required
def asignar_equipo(request, equipo_id):
    """Asignar equipo a un funcionario (solo administradores)"""
    if request.user.role not in ('ADMIN', 'SECRETARIA'):
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('dashboard')

    equipo = get_object_or_404(Equipo, id=equipo_id)

    if equipo.estado == 'ASIGNADO':
        messages.warning(request, 'Este equipo ya está asignado.')
        return redirect('lista_equipos')

    if request.method == 'POST':
        funcionario_id = request.POST.get('funcionario')
        try:
            funcionario = CustomUser.objects.get(id=funcionario_id)

            # Crear préstamo
            PrestamoEquipo.objects.create(
                equipo=equipo,
                funcionario=funcionario,
                observaciones=request.POST.get('observaciones', ''),
                asignado_por=request.user,
                activo=True
            )

            messages.success(request, f'Equipo asignado a {funcionario.get_full_name()}')
            return redirect('lista_equipos')
        except CustomUser.DoesNotExist:
            messages.error(request, 'Funcionario no encontrado.')

    # Obtener TODOS los usuarios activos (no solo FUNCIONARIO)
    funcionarios = CustomUser.objects.filter(
        is_active=True
    ).order_by('last_name', 'first_name')

    context = {
        'equipo': equipo,
        'funcionarios': funcionarios
    }
    return render(request, 'equipos/asignar_equipo.html', context)


@login_required
def mis_equipos(request):
    """Ver equipos asignados al usuario actual"""
    prestamos = PrestamoEquipo.objects.filter(
        funcionario=request.user,
        activo=True
    ).select_related('equipo')

    # Contar número de laptops
    laptops_count = prestamos.filter(equipo__tipo='LAPTOP').count()

    context = {
        'prestamos': prestamos,
        'laptops_count': laptops_count
    }
    return render(request, 'equipos/mis_equipos.html', context)


@login_required
def devolver_equipo(request, prestamo_id):
    """Devolver equipo (solo administradores)"""
    if request.user.role not in ('ADMIN', 'SECRETARIA'):
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('dashboard')

    prestamo = get_object_or_404(PrestamoEquipo, id=prestamo_id)

    if request.method == 'POST':
        prestamo.activo = False
        prestamo.fecha_devolucion = timezone.now().date()
        prestamo.save()
        messages.success(request, f'Equipo {prestamo.equipo} devuelto exitosamente.')
        return redirect('lista_equipos')

    context = {'prestamo': prestamo}
    return render(request, 'equipos/devolver_equipo.html', context)


@login_required
def reporte_prestamos_pdf(request, usuario_id=None):
    """Generar reporte PDF de préstamos. Si se pasa usuario_id, filtra por ese usuario."""
    # Identificar el ID del usuario para el reporte
    uid = usuario_id or request.GET.get('usuario_id')

    # Validación de permisos: Solo ADMIN/SECRETARIA o el propio usuario para su reporte
    if request.user.role not in ('ADMIN', 'SECRETARIA'):
        if not uid or str(request.user.id) != str(uid):
            messages.error(request, 'No tienes permisos para acceder a esta sección.')
            return redirect('dashboard')

    if uid:
        funcionario = get_object_or_404(CustomUser, id=uid)
        prestamos = PrestamoEquipo.objects.filter(
            funcionario=funcionario
        ).select_related('equipo', 'funcionario').order_by('-fecha_asignacion')
        titulo = f'Reporte de Equipos - {funcionario.get_full_name()}'
        filename = f'equipos_{funcionario.last_name}_{datetime.now().strftime("%Y%m%d")}.pdf'
    else:
        prestamos = PrestamoEquipo.objects.select_related('equipo', 'funcionario').all()
        titulo = 'Reporte General de Préstamos de Equipos'
        filename = f'reporte_prestamos_{datetime.now().strftime("%Y%m%d")}.pdf'

    # Agrupar por funcionario
    prestamos_por_usuario = {}
    for prestamo in prestamos:
        key = prestamo.funcionario.id
        if key not in prestamos_por_usuario:
            prestamos_por_usuario[key] = {
                'funcionario': prestamo.funcionario,
                'prestamos': []
            }
        prestamos_por_usuario[key]['prestamos'].append(prestamo)

    # Generar PDF
    html_string = render(request, 'equipos/reporte_prestamos.html', {
        'prestamos_por_usuario': prestamos_por_usuario,
        'titulo': titulo,
        'fecha': timezone.now()
    }).content.decode('utf-8')

    pdf = HTML(string=html_string).write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def reportar_falla(request, equipo_id):
    """Permite a un funcionario reportar una falla en un equipo que tiene asignado"""
    equipo = get_object_or_404(Equipo, id=equipo_id)
    
    # Verificar que el equipo esté asignado al usuario actual
    if not PrestamoEquipo.objects.filter(equipo=equipo, funcionario=request.user, activo=True).exists():
        messages.error(request, 'No puedes reportar fallas de un equipo que no tienes asignado.')
        return redirect('mis_equipos')
    
    if request.method == 'POST':
        descripcion = request.POST.get('descripcion')
        if not descripcion:
            messages.error(request, 'Debes proporcionar una descripción de la falla.')
        else:
            FallaEquipo.objects.create(
                equipo=equipo,
                funcionario=request.user,
                descripcion=descripcion
            )
            messages.success(request, 'Falla reportada correctamente. El administrador será notificado.')
        return redirect('mis_equipos')
    
    return redirect('mis_equipos')


@login_required
def gestion_fallas(request):
    """Panel para que los administradores gestionen los reportes de fallas"""
    if request.user.role not in ('ADMIN', 'SECRETARIA'):
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('dashboard')
    
    fallas = FallaEquipo.objects.select_related('equipo', 'funcionario').order_by('-fecha_reporte')
    return render(request, 'equipos/gestion_fallas.html', {'fallas': fallas})


@login_required
def actualizar_estado_falla(request, falla_id):
    """Actualiza el estado de un reporte de falla"""
    if request.user.role not in ('ADMIN', 'SECRETARIA'):
        messages.error(request, 'No tienes permisos para esta acción.')
        return redirect('dashboard')
    
    falla = get_object_or_404(FallaEquipo, id=falla_id)
    
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        comentarios = request.POST.get('comentarios_tecnicos')
        
        if nuevo_estado in dict(FallaEquipo.ESTADO_FALLA_CHOICES):
            falla.estado = nuevo_estado
            falla.comentarios_tecnicos = comentarios
            falla.resuelto_por = request.user
            falla.save()
            messages.success(request, f'Estado de la falla actualizado a {falla.get_estado_display()}.')
        else:
            messages.error(request, 'Estado no válido.')
            
    return redirect('gestion_fallas')
