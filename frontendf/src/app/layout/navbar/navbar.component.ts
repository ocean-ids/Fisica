import { Component, Input, OnInit, Output, EventEmitter } from '@angular/core';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../services/auth.service';
import { Router } from '@angular/router';
import { MatMenuModule } from '@angular/material/menu';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { ProfileDialogComponent } from '../profile/profile-dialog.component';
import { GlobalFilterStateService } from '../../services/global-filter-state.service';
import { FormsModule } from '@angular/forms';
import { AsignacionService } from '../../services/asignacion.service';
import { VacantesModalComponent } from './vacantes-modal.component';


@Component({
  selector: 'app-navbar',
  imports: [MatToolbarModule, MatIconModule, MatButtonModule, CommonModule, MatMenuModule, MatDialogModule, FormsModule],
  templateUrl: './navbar.component.html',
  styleUrl: './navbar.component.css'
})
export class NavbarComponent implements OnInit {
  @Input() username?: string;
  @Output() toggleSidebar = new EventEmitter<void>();
  fullName: string = '';
  photoUrl: string | null = null;
  themeMode: 'light' | 'dark' = 'light';
  searchText: string = '';
  vacantesCount = 0;
  private vacantesCargando = false;

  constructor(
    private authService: AuthService,
    private router: Router,
    private dialog: MatDialog,
    private globalFilter: GlobalFilterStateService,
    private asignacionService: AsignacionService
  ){}

  onSearchChange(): void {
    this.globalFilter.setQuery(this.searchText, this.router.url);
  }

  ngOnInit(): void {
    // Obtener usuario desde localStorage en lugar de hacer petición al backend
    const user = this.authService.getUserFromStorage();
    if (user) {
      this.username = user.username;
      this.fullName = user.full_name || [user.first_name, user.last_name].filter(Boolean).join(' ');
      this.photoUrl = user.photo_url || null;
    }

    const storedTheme = localStorage.getItem('themeMode');
    this.themeMode = storedTheme === 'dark' ? 'dark' : 'light';
    this.applyThemeClass();

    this.cargarVacantesCount();
    // Refrescar el contador cuando se crean/editan/eliminan asignaciones
    this.asignacionService.asignacionesChanged$.subscribe(() => this.cargarVacantesCount());
  }

  private getMesAnio(): { mes: number; anio: number } {
    const now = new Date();
    return { mes: now.getMonth() + 1, anio: now.getFullYear() };
  }

  private cargarVacantesCount(): void {
    const { mes, anio } = this.getMesAnio();
    this.asignacionService.obtenerAsignacionesVacantes(mes, anio).subscribe({
      next: res => this.vacantesCount = res.total || 0,
      error: () => this.vacantesCount = 0
    });
  }

  abrirVacantes(): void {
    if (this.vacantesCargando) return;
    this.vacantesCargando = true;
    const { mes, anio } = this.getMesAnio();
    const meses = ['ENERO','FEBRERO','MARZO','ABRIL','MAYO','JUNIO','JULIO','AGOSTO','SEPTIEMBRE','OCTUBRE','NOVIEMBRE','DICIEMBRE'];
    this.asignacionService.obtenerAsignacionesVacantes(mes, anio).subscribe({
      next: res => {
        this.vacantesCount = res.total || 0;
        this.vacantesCargando = false;
        this.dialog.open(VacantesModalComponent, {
          width: '720px',
          maxWidth: '95vw',
          data: { vacantes: res.results || [], mesLabel: `${meses[mes - 1]} ${anio}` }
        });
      },
      error: () => {
        this.vacantesCargando = false;
        this.dialog.open(VacantesModalComponent, {
          width: '720px',
          data: { vacantes: [], mesLabel: `${meses[mes - 1]} ${anio}` }
        });
      }
    });
  }

  toggleTheme(): void {
    this.themeMode = this.themeMode === 'light' ? 'dark' : 'light';
    localStorage.setItem('themeMode', this.themeMode);
    this.applyThemeClass();
  }

  get isLightMode(): boolean {
    return this.themeMode === 'light';
  }

  private applyThemeClass(): void {
    document.body.classList.remove('theme-light', 'theme-dark');
    document.body.classList.add(`theme-${this.themeMode}`);
  }

  logout(): void{
    this.authService.logout().subscribe({
      next: () =>{
        this.router.navigate(['/login']);
      },
      error: (error)=>{
        console.log('Error al cerrar sesión');
        this.router.navigate(['/login']);
      }
    });
  }

  onToggleSidebar(): void {
    this.toggleSidebar.emit();
  }

  openProfile(): void {
    const dialogRef = this.dialog.open(ProfileDialogComponent, {
      width: '420px',
      data: {
        fullName: this.fullName || this.username || '',
        photoUrl: this.photoUrl
      }
    });

    dialogRef.afterClosed().subscribe((result?: any) => {
      if (!result?.updated) return;
      const user = this.authService.getUserFromStorage();
      this.fullName = user?.full_name || this.fullName;
      this.photoUrl = user?.photo_url || null;
    });
  }

}
