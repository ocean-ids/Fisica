import { Component } from '@angular/core';
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
export class SidebarComponent {
  allMenuItems = [
    { path: '/dashboard/clientes', label: 'Clientes', icon: 'business', permission: 'CoreFisica.view_cliente' },
    { path: '/dashboard/instalaciones', label: 'Instalaciones', icon: 'location_city', permission: 'CoreFisica.view_instalacion' },
    { path: '/dashboard/puestos', label: 'Puestos', icon: 'work', permission: 'CoreFisica.view_puesto' },
    { path: '/dashboard/personas', label: 'Personal', icon: 'people', permission: 'CoreFisica.view_persona' },
    { path: '/dashboard/horarios', label: 'Horarios', icon: 'schedule', permission: 'CoreFisica.view_horario' },
    { path: '/dashboard/asignaciones', label: 'Asignaciones', icon: 'how_to_reg', permission: 'CoreFisica.view_asignacion' },
    { path: '/dashboard/reporte-asistencia', label: 'Reportes Asistencia', icon: 'assignment_ind', permission: 'CoreFisica.view_reporteasistencia' },
  ];

  constructor(private authService: AuthService) {}

  get menuItems() {
    return this.allMenuItems.filter(item => !item.permission || this.authService.hasPermission(item.permission));
  }
}
