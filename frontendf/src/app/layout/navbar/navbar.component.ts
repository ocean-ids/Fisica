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
  puedeVerAsignaciones = false;
  private vacantesCargando = false;

  // Navegación de coincidencias dentro del buscador.
  matchCount = 0;
  matchIndex = 0;
  private matchRoute = '';

  constructor(
    private authService: AuthService,
    private router: Router,
    private dialog: MatDialog,
    private globalFilter: GlobalFilterStateService,
    private asignacionService: AsignacionService
  ){}

  onSearchChange(): void {
    // Forzar mayúsculas: los datos se guardan en mayúscula, así el filtro coincide siempre.
    const upper = (this.searchText || '').toUpperCase();
    if (upper !== this.searchText) {
      this.searchText = upper;
    }
    this.globalFilter.setQuery(this.searchText, this.router.url);
  }

  // Mostrar flechas solo cuando hay más de una coincidencia en la ruta actual.
  get mostrarMatchNav(): boolean {
    return this.matchCount > 1 && !!this.router.url && this.router.url.startsWith(this.matchRoute || '###');
  }

  coincidenciaSiguiente(): void {
    this.globalFilter.emitMatchNavAction('next');
  }

  coincidenciaAnterior(): void {
    this.globalFilter.emitMatchNavAction('prev');
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

    this.puedeVerAsignaciones = this.authService.hasPermission('CoreFisica.view_asignacion');
    if (this.puedeVerAsignaciones) {
      this.cargarVacantesCount();
      // Refrescar el contador cuando se crean/editan/eliminan asignaciones
      this.asignacionService.asignacionesChanged$.subscribe(() => this.cargarVacantesCount());
    }

    // Estado de coincidencias publicado por la página activa (ej. Asignaciones).
    this.globalFilter.matchNav$.subscribe(nav => {
      this.matchCount = nav?.count || 0;
      this.matchIndex = nav?.index || 0;
      this.matchRoute = nav?.route || '';
    });
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
        const ref = this.dialog.open(VacantesModalComponent, {
          width: '720px',
          maxWidth: '95vw',
          data: { vacantes: res.results || [], mesLabel: `${meses[mes - 1]} ${anio}` }
        });
        ref.afterClosed().subscribe((sel: any) => {
          if (!sel?.id) return;
          this.asignacionService.solicitarAbrirAsignacion(sel.id, sel.canton_id ?? null);
          this.router.navigate(['/dashboard/asignaciones']);
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
