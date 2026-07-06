import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonToggle, MatButtonToggleModule } from '@angular/material/button-toggle';
import { ReporteGuardiaService } from '../../services/reporte-guardia.service';
import { ReporteGuardia } from '../../models/reporte-guardia.model';
import { MatDialog } from '@angular/material/dialog';
import { ReporteGuardiaEditDialogComponent } from './reporte-guardia-edit-dialog/reporte-guardia-edit-dialog.component';
import { CrearApoyoDialogComponent } from './crear-apoyo-dialog/crear-apoyo-dialog.component';
import { GlobalFilterStateService } from '../../services/global-filter-state.service';
import { Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { map, distinctUntilChanged, debounceTime } from 'rxjs/operators';
import Swal from 'sweetalert2';

@Component({
  selector: 'app-reporte-guardia',
  imports: [CommonModule, FormsModule, MatButtonToggleModule],
  templateUrl: './reporte-guardia.component.html',
  styleUrl: './reporte-guardia.component.css',
})
export class ReporteGuardiaComponent implements OnInit, OnDestroy {
  filtroFecha = new Date().toISOString().slice(0, 10);
  filtroTurno: 'Diurno' | 'Nocturno' = localStorage.getItem('rg_turno') === 'Nocturno' ? 'Nocturno' : 'Diurno';
  loading = false;
  filas: ReporteGuardia[] = [];
  busqueda = '';

  readonly etiquetas: Record<string, string> = {
    cliente: 'Cliente',
    puesto: 'Puesto',
    persona_nombre: ' Nombre y Apellidos',
    proviene: 'Proviene',
    valor: 'Valor',
    tipo: 'Tipo',
    autorizacion: 'Autorización',
    motivo: 'Motivo',
    fecha_evento: 'Fecha',
  };

  readonly secciones = [
    { key: 'DOBLADAS',     label: 'DOBLADAS',     cols: ['cliente','puesto','persona_nombre','proviene','valor'], total: true },
    { key: 'ADICIONALES',  label: 'ADICIONALES',  cols: ['cliente','puesto','persona_nombre','proviene'], total: false },
    { key: 'ADELANTOS',    label: 'ADELANTOS',    cols: ['cliente','puesto','persona_nombre','proviene','tipo'], total: false },
    { key: 'NO_CUBIERTOS', label: 'NO CUBIERTOS', cols: ['cliente','puesto','autorizacion','motivo'], total: false },
    { key: 'FALTOS',       label: 'FALTOS',       cols: ['cliente','puesto','persona_nombre','motivo'], total: false },
    { key: 'HUECA',        label: 'HUECA',        cols: ['cliente','puesto','motivo','fecha_evento'], total: false },
    { key: 'APOYO',        label: 'APOYO',        cols: ['cliente','puesto','persona_nombre','proviene','motivo'], total: false },
  ];

  // Campos que se pueden editar por sección (los demás salen de solo lectura).
  // APOYO es 100% manual (CRUD): todos sus campos son editables.
  readonly editablesPorSeccion: Record<string, string[]> = {
    DOBLADAS: [], ADICIONALES: [], ADELANTOS: [],
    NO_CUBIERTOS: ['autorizacion', 'motivo'],
    FALTOS: ['motivo'], HUECA: ['motivo'],
    APOYO: ['cliente', 'puesto', 'persona_nombre', 'proviene', 'motivo'],
  };

  editablesDe(seccion: string): string[] {
    return this.editablesPorSeccion[seccion] || [];
  }

  // APOYO: crear una fila manual (solo vive en el reporte de guardia).
  crearApoyo(): void {
    this.abrirDialogApoyo(null);
  }

  // Crear/editar APOYO con selects (cliente, puesto) + persona filtrable.
  private abrirDialogApoyo(row: ReporteGuardia | null): void {
    const ref = this.dialog.open(CrearApoyoDialogComponent, {
      width: '520px',
      maxWidth: '95vw',
      data: { row: row || undefined },
    });
    ref.afterClosed().subscribe((res) => {
      if (!res) { return; }
      if (row?.id) {
        this.srv.actualizar(row.id, res).subscribe({ next: () => this.cargar(), error: () => this.cargar() });
      } else {
        this.srv.crear({ ...res, seccion: 'APOYO', fecha: this.filtroFecha, turno: this.filtroTurno } as any).subscribe({
          next: () => this.cargar(),
          error: () => this.cargar(),
        });
      }
    });
  }

  // APOYO: eliminar una fila manual.
  eliminar(f: ReporteGuardia): void {
    if (!f.id) { return; }
    Swal.fire({
      title: '¿Eliminar apoyo?',
      text: `${f.puesto || ''} ${f.persona_nombre || ''}`.trim(),
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar',
    }).then((r) => {
      if (r.isConfirmed) {
        this.srv.eliminar(f.id!).subscribe({ next: () => this.cargar(), error: () => this.cargar() });
      }
    });
  }

  celda(f: any, campo: string): string {
    const v = f?.[campo];
    if (campo === 'valor') return v ? Number(v).toFixed(2) : '';
    if (campo === 'fecha_evento' || campo === 'fecha') return this.fechaDMA(v);
    return v ?? '';
  }

  private fechaDMA(v: any): string {
    if (!v) return '';
    const [y, m, d] = String(v).slice(0, 10).split('-');
    return (y && m && d) ? `${d}/${m}/${y}` : String(v);
  }

  totalValor(key: string): number {
    return this.filasDe(key).reduce((s, f) => s + Number(f.valor || 0), 0);
  }

  editar(f: ReporteGuardia): void {
    if (!f.id) { return; }
    // APOYO se edita con el mismo formulario de selects que al crear.
    if (f.seccion === 'APOYO') { this.abrirDialogApoyo(f); return; }
    const editables = this.editablesDe(f.seccion);
    if (!editables.length) { return; }
    const sec = this.secciones.find(s => s.key === f.seccion);
    const campos = (sec?.cols || []).filter(c => !editables.includes(c));
    const ref = this.dialog.open(ReporteGuardiaEditDialogComponent, {
      width: '640px',
      maxWidth: '95vw',
      data: { row: { ...f }, campos, editables, etiquetas: this.etiquetas },
    });
    ref.afterClosed().subscribe((res) => {
      if (!res) { return; }
      this.srv.actualizar(f.id!, res).subscribe({
        next: () => { Object.assign(f, res); },
        error: () => { this.cargar(); },
      });
    });
  }


  private filterSub?: Subscription;

  constructor(
    private srv: ReporteGuardiaService,
    private dialog: MatDialog,
    private globalFilter: GlobalFilterStateService,
    private router: Router,
  ){}

  ngOnInit(): void {
    this.cargar();

    // Buscador global del navbar: filtra en vivo las filas ya cargadas.
    this.filterSub = this.globalFilter.state$.pipe(
      map(state => {
        if (!this.router.url.startsWith('/dashboard/reporte-guardia')) return null;
        const route = (state?.route || '').toString();
        if (route && !route.startsWith('/dashboard/reporte-guardia')) return null;
        return (state?.query || '').trim();
      }),
      distinctUntilChanged(),
      debounceTime(300),
    ).subscribe(query => {
      if (query === null) return;
      this.busqueda = query;
    });
  }

  ngOnDestroy(): void {
    this.filterSub?.unsubscribe();
  }

  cargar(): void {
    localStorage.setItem('rg_turno', this.filtroTurno);
    this.loading = true;
    this.srv.listar(this.filtroFecha, this.filtroTurno).subscribe({
      next: (rows) => { this.filas = rows || []; this.loading = false; },
      error: () => { this.filas = []; this.loading = false; },
    });
  }


  onFechaChange(e: Event): void{
    this.filtroFecha = (e.target as HTMLInputElement).value;
    this.cargar()
  }

  filasDe(seccion: string): ReporteGuardia[] {
    const q = this.busqueda.trim().toLowerCase();
    return this.filas.filter(f => {
      if (f.seccion !== seccion) { return false; }
      if (!q) { return true; }
      return [f.cliente, f.puesto, f.persona_nombre, f.proviene, f.motivo, f.tipo, f.autorizacion]
        .some(v => (v || '').toString().toLowerCase().includes(q));
    });
  }

}
