import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { ReporteAsistenciaService } from '../../services/reporte-asistencia.service';
import { ReporteAsistenciaEditDialogComponent } from './dialogs/reporte-asistencia-edit-dialog.component';
import { ReporteAsistenciaHistorialItem, ReporteAsistenciaRow, ResumenAsistencia, ResumenAsistenciaZona } from '../../models';
import { ReporteAsistenciaColorDialogComponent } from './dialogs/reporte-asistencia-color-dialog.component';
import { FormsModule } from '@angular/forms';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { PersonaService } from '../../services/persona.service';
import { PersonaFormComponent } from '../personas/persona-form/persona-form.component';
import { MAT_BOTTOM_SHEET_DATA, MatBottomSheet, MatBottomSheetModule, MatBottomSheetRef } from '@angular/material/bottom-sheet';
import { ReporteEstadoComponent } from './reporte-estado/reporte-estado.component';
import { ReporteAsistenciaHistorialDialogComponent } from './dialogs/reporte-asistencia-historial-dialog.component';
import Swal from 'sweetalert2';
import { GlobalFilterStateService } from '../../services/global-filter-state.service';
import { Router } from '@angular/router';
import { Subscription, debounceTime, distinctUntilChanged, map } from 'rxjs';

interface ReporteAsistenciaGrupoProvincia {
  provincia: string;
  rows: ReporteAsistenciaRow[];
}

interface ReporteAsistenciaGrupoZona {
  zona: string;
  provincias: ReporteAsistenciaGrupoProvincia[];
}

@Component({
  selector: 'app-reporte-asistencia',
  standalone: true,
  imports: [CommonModule, MatButtonModule, FormsModule, MatButtonToggleModule, MatBottomSheetModule],
  templateUrl: './reporte-asistencia.component.html',
  styleUrl: './reporte-asistencia.component.css'
})
export class ReporteAsistenciaComponent implements OnInit, OnDestroy {
  reporte: ReporteAsistenciaRow[] = [];
  reporteAgrupado: ReporteAsistenciaGrupoZona[] = [];
  resumen: ResumenAsistencia = { total: 0, asistencias: 0, faltas: 0 };
  loading = false;
  historialPorAsignacion: Record<number, ReporteAsistenciaHistorialItem[]> = {};
  filtroFecha = '';
  filtroClienteId = '';
  filtroFechaDisplay = '';
  filtroTurno = '';
  filtroZona = 'Zona 1';

  readonly zonaOpciones = ['', 'Zona 1', 'Zona 2', 'Zona 3'];
  readonly pageSizeOptions = [25, 50, 100];
  currentPage = 1;
  pageSize = 50;
  totalItems = 0;
  totalPages = 1;
  filtroTexto = '';
  private filterSub?: Subscription;


  readonly colorPalette: {name: string, value: string}[] = [
    { name: 'Amarillo', value: '#fff8b3' },
    { name: 'Rojo', value: '#ffb3b3' },
    { name: 'Verde', value: '#b3ffb3' },
    { name: 'Azul', value: '#b3d9ff' },
    { name: 'Naranja', value: '#ffd9b3' },
    { name: 'Verde Lima', value: '#2ff968' },
    { name: 'Gris', value: '#d9d9d9' },
    { name: 'Celeste', value: '#b3e6ff' },
    { name: 'Rosa', value: '#ffb3e6' },
    { name: 'Beige', value: '#f5f5dc' },
    { name: 'Lima', value: '#d9ffb3' },
    { name: 'Turquesa', value: '#b3fff0' },
    { name: 'Lavanda', value: '#e6b3ff' },
    { name: 'Mostaza', value: '#ffdb58' },
    { name: 'Coral', value: '#ff7f50' },
    { name: 'Cian', value: '#00ffff' },
    { name: 'Crema', value: '#fffdd0' },
    { name: 'Caqui', value: '#f0e68c' },
    { name: 'Salmón', value: '#fa8072' },
    { name: 'Blanco', value: '#ffffff' },
  ];

  constructor(
    private reporteSvc: ReporteAsistenciaService,
    private dialog: MatDialog,
    private personaService: PersonaService,
    private bottomSheet: MatBottomSheet,
    private globalFilter: GlobalFilterStateService,
    private router: Router
    
  ) {}

  ngOnInit(): void {
    this.setHoy();
    this.filtroTurno = 'Diurno';
    this.cargarReporte();

    this.filterSub = this.globalFilter.state$
      .pipe(
        map(state => {
          if (!this.router.url.startsWith('/dashboard/reporte-asistencia')) return null;
          const route = (state?.route || '').toString();
          if (route && !route.startsWith('/dashboard/reporte-asistencia')) return null;
          return (state?.query || '').trim();
        }),
        distinctUntilChanged(),
        debounceTime(300)
      )
      .subscribe(query => {
        if (query === null) return;
        this.filtroTexto = query;
        this.cargarReporte(true, false);
      });
  }

  ngOnDestroy(): void {
    this.filterSub?.unsubscribe();
  }

  private getZonaOrden(zona: string): number {
    const z = (zona || '').trim().toLowerCase();
    if (z === 'zona 1') return 0;
    if (z === 'zona 2') return 1;
    if (z === 'zona 3') return 2;
    return 99;
  }

  getZonaTitulo(zona: string): string {
    const normalized = (zona || '').trim().toLowerCase();
    if (normalized === 'zona 1') return 'ZONA 1 / DAULE - SAMBORONDON';
    if (normalized === 'zona 2') return 'ZONA 2 / SUR - CENTRO';
    if (normalized === 'zona 3') return 'ZONA 3 / DAULE - NORTE';
    return (zona || '').toUpperCase();
  }

  private buildReporteAgrupado(): ReporteAsistenciaGrupoZona[] {
    const zonas: Record<string, Record<string, ReporteAsistenciaRow[]>> = {};
    for (const row of this.reporte) {
      const isBaseLibre = !row.asignacion_id
        && (row.descripcion || '').toString().trim().toLowerCase().includes('libre en base');
      if (!row.asignacion_id && !isBaseLibre) {
        continue;
      }
      let zona = (row.zona_titulo || '').trim() || 'SIN ZONA';
      let provincia = (row.provincia || '').trim() || 'SIN PROVINCIA';
      if (!zonas[zona]) zonas[zona] = {};
      if (!zonas[zona][provincia]) zonas[zona][provincia] = [];
      zonas[zona][provincia].push(row);
    }

    return Object.keys(zonas)
      .sort((a, b) => {
        const diff = this.getZonaOrden(a) - this.getZonaOrden(b);
        return diff !== 0 ? diff : a.localeCompare(b);
      })
      .map((zona) => {
        const provincias = Object.keys(zonas[zona])
          .sort((a, b) => a.localeCompare(b))
          .map((provincia) => ({ provincia, rows: zonas[zona][provincia] }));
        return { zona, provincias };
      });
  }

  private setHoy(): void {
    const hoy = new Date();
    const isoLocal = new Date(hoy.getTime() - hoy.getTimezoneOffset() * 60000)
      .toISOString()
      .slice(0, 10);
    this.filtroFecha = isoLocal;
    this.filtroFechaDisplay = isoLocal.split('-').reverse().join('/');
  }

  onRowDoubleClick(row: ReporteAsistenciaRow): void {
    if (!row?.asignacion_id) return;

    const dialogRef = this.dialog.open(ReporteAsistenciaColorDialogComponent, {
      width: '420px',
      maxWidth: '95vw',
      data: {
        selectedColor: row.row_color || this.colorPalette[0].value,
        palette: this.colorPalette
      }
    });

    dialogRef.afterClosed().subscribe((selectedColor?: string) => {
      if (!selectedColor || !row.asignacion_id) return;

      const payload = {
        row_color: selectedColor,
        fecha: this.filtroFecha || null,
      };

      this.reporteSvc.updateReporteAsistencia(row.asignacion_id, payload).subscribe({
        next: (res) => {
          row.row_color = res.row_color || selectedColor;
        },
        error: (err) => this.handleActionError(err, 'No se pudo actualizar el color')
      });
    });
  }

  getRowColor(row: ReporteAsistenciaRow): string {
    return row.row_color || '';
  }

  abrirModalNuevaPersona(): void {
      const dialogRef = this.dialog.open(PersonaFormComponent, {
        width: '600px',
        data: {}
      });

      dialogRef.afterClosed().subscribe(result => {
        if (!result) return;
        this.personaService.createPersona(result).subscribe({
          next: () => {
            Swal.fire({ icon: 'success', title: 'Persona creada', timer: 1200, showConfirmButton: false });
            this.cargarReporte();
          },
          error: (err) => this.handleActionError(err, 'No se pudo crear persona')
        });
      });
  }

  openBottomSheet(): void {
    this.bottomSheet.open(ReporteEstadoComponent, {
      data: this.buildResumenAsistencia()
    });
  }

  private hasReemplazo(row: ReporteAsistenciaRow): boolean {
    return (row.estado_asistencia || '') === 'FALTO';
  }

  private buildResumenAsistencia(): ResumenAsistencia {
    const filas = this.reporte.filter(r => !! r.asignacion_id);
    const faltas = filas.filter(r => this.hasReemplazo(r)).length;
    const total = filas.length;
    const por_zona = this.buildResumenPorZona(filas);
    return { total, asistencias: total - faltas, faltas, por_zona };
  }

  private buildResumenPorZona(filas: ReporteAsistenciaRow[]): ResumenAsistenciaZona[] {
    const zonas: Record<string, { total: number; faltas: number }> = {};
    for (const row of filas) {
      const zona = (row.zona_titulo || '').trim() || 'SIN ZONA';
      if (!zonas[zona]) zonas[zona] = { total: 0, faltas: 0 };
      zonas[zona].total += 1;
      if (this.hasReemplazo(row)) zonas[zona].faltas += 1;
    }

    return Object.keys(zonas)
      .sort((a, b) => {
        const diff = this.getZonaOrden(a) - this.getZonaOrden(b);
        return diff !== 0 ? diff : a.localeCompare(b);
      })
      .map((zona) => ({
        zona,
        total: zonas[zona].total,
        faltas: zonas[zona].faltas,
        asistencias: Math.max(zonas[zona].total - zonas[zona].faltas, 0),
      }));
  }

  descargarExcel(): void {
    const params: any = {};
    if (this.filtroTexto) params.q = this.filtroTexto;
    if (this.filtroFecha) params.fecha = this.filtroFecha;
    if (this.filtroClienteId) params.cliente_id = this.filtroClienteId;
    if (this.filtroZona) params.zona = this.filtroZona;
    if (this.filtroTurno) params. turno = this.filtroTurno;
    this.reporteSvc.exportarExcel(params).subscribe({
      next: (blog) => this.descargarArchivo(blog, `reporte_asistencia_${this.filtroFecha}.xlsx`),
      error: (err) => this.handleDownloadError(err, 'Excel')
    });
  }

  descargarPdf(): void {
    const params: any = {};
    if (this.filtroTexto) params.q = this.filtroTexto;
    if(this.filtroFecha) params.fecha = this.filtroFecha;
    if(this.filtroClienteId) params.cliente_id = this.filtroClienteId;
    if(this.filtroZona) params.zona = this.filtroZona;
    if(this.filtroTurno) params.turno = this.filtroTurno;
    this.reporteSvc.exportarPdf(params).subscribe({
      next: (blog) => this.descargarArchivo(blog, `reporte_asistencia_${this.filtroFecha}.pdf`),
      error: (err) => this.handleDownloadError(err, 'PDF')
    })
  }

  private handleDownloadError(err: any, tipo: string): void {
    const status = err?.status;
    const msg = status === 403
      ? 'No autorizado'
      : `No se pudo descargar el ${tipo}`;
    Swal.fire({ icon: 'error', title: 'Error', text: msg });
  }

  private handleActionError(err: any, fallback: string): void {
    const status = err?.status;
    const msg = status === 403 ? 'No autorizado' : fallback;
    Swal.fire({ icon: 'error', title: 'Error', text: msg });
  }

  private descargarArchivo(blob: Blob, nombre: string): void {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = nombre;
    a.click();
    window.URL.revokeObjectURL(url);
  }

  cargarReporte(resetPage: boolean = false, showLoader: boolean = true): void {
    if (resetPage) {
      this.currentPage = 1;
    }
    const params: any = {};
    if (this.filtroTexto) params.q = this.filtroTexto;
    if (this.filtroFecha) params.fecha = this.filtroFecha;
    if (this.filtroClienteId) params.cliente_id = this.filtroClienteId;
    if (this.filtroZona) params.zona = this.filtroZona;
    if (this.filtroTurno) params.turno = this.filtroTurno;
    params.page = this.currentPage;
    params.page_size = this.pageSize;
    if (showLoader) {
      this.loading = true;
    }
    this.reporteSvc.getReporteAsistencia(params).subscribe({
      next: data=> {
        this.reporte = data?.results || [];
        this.totalItems = Number(data?.total || 0);
        this.currentPage = Number(data?.page || this.currentPage);
        this.pageSize = Number(data?.page_size || this.pageSize);
        this.totalPages = Math.max(1, Number(data?.total_pages || 1));
        this.reporteAgrupado = this.buildReporteAgrupado();
        this.resumen = this.buildResumenAsistencia();
      },
      error: err => this.handleActionError(err, 'No se pudo cargar reporte de asistencia'),
      complete: () => {
        if (showLoader) {
          this.loading = false;
        }
      }
    });
  }

  abrirModalEdicion(row: ReporteAsistenciaRow): void {
    if (!row?.asignacion_id) return;

    const occupiedReemplazoIds = Array.from(new Set(
      (this.reporte || [])
        .filter((r) => !!r?.reemplazo_id && r.asignacion_id !== row.asignacion_id)
        .map((r) => Number(r.reemplazo_id))
        .filter((id) => Number.isFinite(id) && id > 0)
    ));

    const dialogRef = this.dialog.open(ReporteAsistenciaEditDialogComponent, {
      width: '700px',
      maxWidth: '95vw',
      data: {
        row: { ...row },
        fecha: this.filtroFecha || null,
        occupiedReemplazoIds,
      }
    });

    dialogRef.afterClosed().subscribe((res) => {
      if (!res) return;
      row.codigo = res.codigo;
      row.estado_asistencia = res.estado_asistencia;
      row.estado = res.estado;
      row.descripcion = res.descripcion;
      row.reemplazo_id = res.reemplazo_id;
      row.reemplazo = res.reemplazo;
      row.modificado_por = res.modificado_por;
      row.modificado_en = res.modificado_en;
    });
  }

  abrirHistorialModal(row: ReporteAsistenciaRow): void {
    if (!row?.asignacion_id) return;

    this.dialog.open(ReporteAsistenciaHistorialDialogComponent, {
      width: '720px',
      maxWidth: '95vw',
      data: {
        asignacionId: row.asignacion_id,
        codigo: row.codigo || null,
        fecha: this.filtroFecha || null
      }
    });
  }

  limpiarFiltros(): void {
    this.setHoy();
    this.filtroClienteId = '';
    this.filtroTurno = '';
    this.filtroZona = 'Zona 1';
    this.currentPage = 1;
    this.cargarReporte(true);
  }

  onFechaChange(event: Event): void {
    const iso = (event.target as HTMLInputElement).value;
    this.filtroFecha = iso || '';
    this.filtroFechaDisplay = iso ? iso.split('-').reverse().join('/') : '';
    this.cargarReporte(true);
  }

  onZonaChange(event: Event): void {
    const zona = (event.target as HTMLSelectElement).value || '';
    this.filtroZona = zona;
    this.cargarReporte(true);
  }

  onPageSizeChange(event: Event): void {
    const size = Number((event.target as HTMLSelectElement).value);
    if (!size || size < 1) return;
    this.pageSize = size;
    this.cargarReporte(true);
  }

  goToPage(page: number): void {
    if (page < 1 || page > this.totalPages || page === this.currentPage) return;
    this.currentPage = page;
    this.cargarReporte();
  }

  prevPage(): void {
    this.goToPage(this.currentPage - 1);
  }

  nextPage(): void {
    this.goToPage(this.currentPage + 1);
  }

  estadoClass(estado?: string): string {
    const value = (estado || '').trim().toUpperCase();
    if (value === 'TURNO') return 'badge bg-success';
    if (value === 'ADICIONAL') return 'badge bg-warning text-dark';
    if (value === 'EVENTUAL') return 'badge bg-info text-dark';
    if (value === 'ADEL/TURNO') return 'badge bg-secondary';
    if (value === 'DOBLA' || value === 'DOBLADO') return 'badge badge-turno-dobla';
    if (value === 'FR/TRABAJADO') return 'badge bg-light text-dark border';
    if (value === 'RETEN') return 'badge bg-secondary';
    if (value === 'CUSTODIO') return 'badge bg-info';
    return 'badge bg-secondary';
  }
  

  estadoAsistenciaClass(estadoAsistencia?: string | null): string {
    if (estadoAsistencia === 'FALTO') return 'badge bg-danger';
    if (estadoAsistencia === 'ASISTIO') return 'badge bg-primary';
    return 'badge bg-secondary';
  }

  estadoAsistenciaLabel(estadoAsistencia?: string | null): string {
    if (estadoAsistencia === 'ASISTIO') return 'ASISTE';
    if (estadoAsistencia === 'FALTO') return 'FALTO';
    return '-';
  }
}
