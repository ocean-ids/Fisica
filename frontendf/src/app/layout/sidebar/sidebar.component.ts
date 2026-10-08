import { Component, OnInit } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-sidebar',
  imports: [RouterLink, RouterLinkActive, MatIconModule],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.css'
})
export class SidebarComponent implements OnInit {
  // Menú agrupado (Operación / Servicios / Catálogos / Pagos). Cada opción mantiene su clave (para ocultarla por
  // usuario desde el admin) y su permiso; un grupo sin opciones visibles no se muestra.
  grupos: Array<{ titulo: string; items: Array<{ key: string; path: string; label: string; icon: string; permission: string }> }> = [
    { titulo: 'Operación', items: [
      { key: 'reporte-asistencia', path: '/dashboard/reporte-asistencia', label: 'Reporte de Asistencia', icon: 'clipboard-check', permission: 'CoreFisica.view_reporteasistencia' },
      { key: 'asignaciones', path: '/dashboard/asignaciones', label: 'Asignaciones', icon: 'calendar3', permission: 'CoreFisica.view_asignacion' },
      { key: 'consolidado', path: '/dashboard/consolidado', label: 'Consolidado', icon: 'journal-text', permission: 'CoreFisica.view_consolidado' },
      { key: 'reporte-guardia', path: '/dashboard/reporte-guardia', label: 'Reporte de Guardia', icon: 'shield-check', permission: 'CoreFisica.view_reporteguardia' },
    ] },
    { titulo: 'Servicios', items: [
      { key: 'eventuales', path: '/dashboard/eventuales', label: 'Eventuales', icon: 'person-plus', permission: 'CoreFisica.view_horaseventual' },
      { key: 'servicios-adicionales', path: '/dashboard/servicios-adicionales', label: 'Adicionales', icon: 'plus-square', permission: 'CoreFisica.view_servicioadicional' },
      { key: 'sacavacaciones', path: '/dashboard/sacavacaciones', label: 'Vacaciones', icon: 'airplane', permission: 'CoreFisica.view_asignacion' },
    ] },
    { titulo: 'Catálogos', items: [
      { key: 'personas', path: '/dashboard/personas', label: 'Personal', icon: 'people', permission: 'CoreFisica.view_persona' },
      { key: 'clientes', path: '/dashboard/clientes', label: 'Clientes', icon: 'building', permission: 'CoreFisica.view_cliente' },
      { key: 'instalaciones', path: '/dashboard/instalaciones', label: 'Instalaciones', icon: 'geo-alt', permission: 'CoreFisica.view_instalacion' },
      { key: 'puestos', path: '/dashboard/puestos', label: 'Puestos', icon: 'briefcase', permission: 'CoreFisica.view_puesto' },
    ] },
    { titulo: 'Pagos', items: [
      { key: 'reporte-pago', path: '/dashboard/reporte-pago', label: 'Reporte de Pagos', icon: 'cash-coin', permission: 'CoreFisica.view_reporteguardia' },
      { key: 'tarifas-pago', path: '/dashboard/tarifas-pago', label: 'Tarifas', icon: 'tags', permission: 'CoreFisica.view_reporteguardia' },
    ] },
  ];

  fullName = '';
  username = '';
  photoUrl: string | null = null;
  puestoName = '';
  cargoName = '';

  constructor(private authService: AuthService) {}

  ngOnInit(): void {
    const user = this.authService.getUserFromStorage();
    if (!user) return;

    this.username = user.username || '';
    this.fullName = user.full_name || [user.first_name, user.last_name].filter(Boolean).join(' ');
    this.photoUrl = user.photo_url || null;
    this.puestoName = this.resolvePuestoName(user);
    this.cargoName = this.resolveCargoName(user);
  }

  // Grupos con sus opciones visibles: permiso de datos Y no ocultas por el admin para este usuario.
  get gruposVisibles() {
    return this.grupos
      .map(g => ({ ...g, items: g.items.filter(item => (!item.permission || this.authService.hasPermission(item.permission))
        && !this.authService.isModuleHidden(item.key)) }))
      .filter(g => g.items.length);
  }

  get displayName(): string {
    return this.fullName || this.username;
  }

  private resolvePuestoName(user: any): string {
    if (typeof user?.puesto_name === 'string') return user.puesto_name;
    if (typeof user?.puesto_nombre === 'string') return user.puesto_nombre;
    if (typeof user?.puesto === 'string') return user.puesto;
    if (typeof user?.puesto?.nombre === 'string') return user.puesto.nombre;
    return '';
  }

  private resolveCargoName(user: any): string {
    if (typeof user?.cargo === 'string') return user.cargo;
    if (typeof user?.role === 'string') return user.role;
    if (typeof user?.position === 'string') return user.position;
    return '';
  }
}
