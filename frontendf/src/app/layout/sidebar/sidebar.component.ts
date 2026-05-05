import { Component, OnInit } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-sidebar',
  imports: [RouterLink, RouterLinkActive, MatListModule, MatIconModule],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.css'
})
export class SidebarComponent implements OnInit {
  allMenuItems = [
    { path: '/dashboard/clientes', label: 'Clientes', icon: 'business', permission: 'CoreFisica.view_cliente' },
    { path: '/dashboard/instalaciones', label: 'Instalaciones', icon: 'location_city', permission: 'CoreFisica.view_instalacion' },
    { path: '/dashboard/puestos', label: 'Puestos', icon: 'work', permission: 'CoreFisica.view_puesto' },
    { path: '/dashboard/personas', label: 'Personal', icon: 'admin_panel_settings', permission: 'CoreFisica.view_persona' },
    { path: '/dashboard/horarios', label: 'Franja Horaria', icon: 'schedule', permission: 'CoreFisica.view_horario' },
    { path: '/dashboard/asignaciones', label: 'Asignaciones', icon: 'how_to_reg', permission: 'CoreFisica.view_asignacion' },
    { path: '/dashboard/reporte-asistencia', label: 'Reportes Asistencia', icon: 'assignment_ind', permission: 'CoreFisica.view_reporteasistencia' },
    { path: '/dashboard/personal-consola', label: 'Personal Consola', icon: 'computer', permission: 'CoreFisica.view_personalconsola' },
    { path: '/dashboard/consolidado', label: 'Consolidado', icon: 'assignment', permission: 'CoreFisica.view_consolidado' },
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

  get menuItems() {
    return this.allMenuItems.filter(item => !item.permission || this.authService.hasPermission(item.permission));
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
