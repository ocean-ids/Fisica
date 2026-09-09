import { Component, OnInit, HostListener } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { NavbarComponent } from '../navbar/navbar.component';
import { SidebarComponent } from '../sidebar/sidebar.component';
import { CommonModule } from '@angular/common';
import { NotificacionService } from '../../services/notificacion.service';
import { ValidarEventualesDialogComponent } from '../validar-eventuales-dialog/validar-eventuales-dialog.component';

@Component({
  selector: 'app-dashboard',
  imports: [RouterOutlet, NavbarComponent, SidebarComponent, CommonModule, MatDialogModule],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css'
})
export class DashboardComponent implements OnInit {
  sidebarVisible: boolean = true;
  isMobile: boolean = false;

  constructor(private dialog: MatDialog, private notifSvc: NotificacionService) {}

  ngOnInit(): void {
    this.isMobile = window.innerWidth < 992;
    if (this.isMobile) {
      // En celular el menú arranca CERRADO (flota por encima al abrirlo).
      this.sidebarVisible = false;
    } else {
      const stored = localStorage.getItem('sidebarVisible');
      if (stored !== null) {
        this.sidebarVisible = stored === 'true';
      }
    }

    this.revisarEventualesPendientes();
  }

  // Al abrir la app: si el usuario tiene eventuales por validar, abre el modal.
  private revisarEventualesPendientes(): void {
    this.notifSvc.listarPendientes().subscribe({
      next: (res) => {
        const pendientes = res?.results || [];
        if (pendientes.length) {
          this.dialog.open(ValidarEventualesDialogComponent, {
            width: '680px',
            maxWidth: '95vw',
            disableClose: false,
            data: { notificaciones: pendientes },
          });
        }
      },
      error: () => { /* silencioso: no molestar si falla la consulta */ },
    });
  }

  @HostListener('window:resize')
  onResize(): void {
    const mobile = window.innerWidth < 992;
    if (mobile !== this.isMobile) {
      this.isMobile = mobile;
      // Al pasar a móvil: cerrar. Al pasar a escritorio: abrir (o preferencia).
      this.sidebarVisible = mobile ? false : (localStorage.getItem('sidebarVisible') !== 'false');
    }
  }

  toggleSidebar(): void {
    this.sidebarVisible = !this.sidebarVisible;
    // La preferencia se guarda solo en escritorio (en móvil siempre arranca cerrado).
    if (!this.isMobile) {
      localStorage.setItem('sidebarVisible', String(this.sidebarVisible));
    }
  }

  // En móvil, al elegir una opción del menú, se cierra solo.
  cerrarEnMovil(): void {
    if (this.isMobile) {
      this.sidebarVisible = false;
    }
  }
}
