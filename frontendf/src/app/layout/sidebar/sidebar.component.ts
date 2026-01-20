import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-sidebar',
  imports: [RouterLink, RouterLinkActive, MatListModule, MatIconModule],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.css'
})
export class SidebarComponent {
  menuItems = [
    { path: '/dashboard/clientes', label: 'Clientes', icon: 'business' },
    { path: '/dashboard/instalaciones', label: 'Instalaciones', icon: 'location_city' },
    { path: '/dashboard/puestos', label: 'Puestos', icon: 'work' },
    { path: '/dashboard/personas', label: 'Personas', icon: 'people' },
    { path: '/dashboard/horarios', label: 'Horarios', icon: 'schedule' }
  ];
}
