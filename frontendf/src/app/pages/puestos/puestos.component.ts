import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { FormsModule } from '@angular/forms';
import { PuestoService } from '../../services/puesto.service';
import { Puesto } from '../../models';
import { ClienteService } from '../../services/cliente.service';
import { Cliente } from '../../models';
import { PuestoFormComponent } from './puesto-form/puesto-form.component';
import { NovedadPuestoDialogComponent } from './novedad-puesto-dialog/novedad-puesto-dialog.component';
import { NovedadPuestoListDialogComponent } from './novedad-puesto-list-dialog/novedad-puesto-list-dialog.component';
import { NovedadPuestoService } from '../../services/novedad-puesto.service';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatMenuModule } from '@angular/material/menu';
import Swal from 'sweetalert2';


@Component({
  selector: 'app-puestos',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatButtonModule,
     MatIconModule,
     MatCardModule,
     MatFormFieldModule,
    MatAutocompleteModule,
    MatSelectModule,
    MatInputModule,
     MatDialogModule,
      FormsModule,
    MatTooltipModule,
    MatMenuModule
  ],
  templateUrl: './puestos.component.html',
  styleUrl: './puestos.component.css'
})
export class PuestosComponent implements OnInit {
  puestos: Puesto[] = [];
  clientes: Cliente[] = [];
  clientesFiltrados: Cliente[] = [];
  clienteSeleccionado: number | null = null;
  clienteSeleccionadoNombre = '';
  clienteFiltro: string | Cliente = '';

  instalaciones: Array<{ id: number; nombre: string }> = [];
  instalacionSeleccionada: number | null = null;

  fechaReporteNovedad = this.hoyISO();

  constructor(
    private puestoService: PuestoService,
    private clienteService: ClienteService,
    private novedadService: NovedadPuestoService,
    private dialog: MatDialog
  ) {}

  private hoyISO(): string {
    const d = new Date();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${d.getFullYear()}-${mm}-${dd}`;
  }

  ngOnInit(): void {
    this.cargarClientes();
  }

  cargarClientes(): void {
    this.clienteService.getClientes().subscribe({
      next: (data) => {
        this.clientes = data;
        this.clientesFiltrados = [...data];
      },
      error: (err) => console.error('Error al cargar clientes', err)
    });
  }

  filtrarClientes(): void {
    const raw = typeof this.clienteFiltro === 'string'
      ? this.clienteFiltro
      : (this.clienteFiltro?.nombre_comercial || '');
    const term = raw.trim().toLowerCase();
    if (!term) {
      this.clientesFiltrados = [...this.clientes];
      this.clienteSeleccionado = null;
      this.clienteSeleccionadoNombre = '';
      this.puestos = [];
      return;
    }

    if (this.clienteSeleccionadoNombre.toLowerCase() !== term) {
      this.clienteSeleccionado = null;
      this.puestos = [];
    }

    this.clientesFiltrados = this.clientes.filter(cliente =>
      (cliente.nombre_comercial || '').toLowerCase().includes(term)
    );
  }

  onClienteSeleccionado(cliente: Cliente): void {
    this.clienteSeleccionado = cliente.id ?? null;
    this.clienteSeleccionadoNombre = cliente.nombre_comercial || '';
    this.clienteFiltro = this.clienteSeleccionadoNombre;
    this.cargarPuestos();
  }

  mostrarCliente = (cliente: Cliente | string | null): string => {
    if (!cliente) return '';
    return typeof cliente === 'string' ? cliente : (cliente.nombre_comercial || '');
  };

  cargarPuestos(): void {
    if (this.clienteSeleccionado) {
      this.puestoService.getPuestosPorCliente(this.clienteSeleccionado).subscribe({
        next: data => {
          this.puestos = data;
          this.instalacionSeleccionada = null;
          // Lista única de instalaciones de los puestos cargados
          const map = new Map<number, string>();
          (data || []).forEach((p: any) => {
            const id = p.instalacion_id;
            const nombre = (p.instalacion_nombre || '').trim();
            if (id && !map.has(id)) map.set(id, nombre || `Instalación ${id}`);
          });
          this.instalaciones = Array.from(map.entries())
            .map(([id, nombre]) => ({ id, nombre }))
            .sort((a, b) => a.nombre.localeCompare(b.nombre));
        },
        error: err => console.error('Error al cargar puestos:', err)
      });
    }
  }

  // Puestos a mostrar según la instalación elegida (o todos si no hay)
  get puestosMostrados(): Puesto[] {
    if (!this.instalacionSeleccionada) return this.puestos;
    return (this.puestos || []).filter((p: any) => p.instalacion_id === this.instalacionSeleccionada);
  }

  abrirFormularioNuevo(puesto?: Puesto): void {
    const dialogRef = this.dialog.open(PuestoFormComponent, {
      width: '780px',
      maxWidth: '95vw',
      data: { puesto: puesto || null, clienteId: this.clienteSeleccionado }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        if (puesto?.id) {
          this.actualizarPuesto(puesto.id, result);
        } else {
          this.crearPuesto(result);
        }
      }
    });
  }

  crearPuesto(data: any): void{
    this.puestoService.crearPuesto(data).subscribe({
      next: () => {
        this.cargarPuestos();
        Swal.fire({ icon: 'success', title: 'Puesto Creado', timer: 1200, showConfirmButton: false });
      },
      error: (err) => {
        console.error('Error al crear puesto', err);
        Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo crear el puesto' });
      }
    });
  }

  actualizarPuesto(id: number, data: any): void {
    this.puestoService.actualizarPuesto(id, data).subscribe({
      next: () => {
        this.cargarPuestos();
        Swal.fire({ icon: 'success', title: 'Puesto Actualizado', timer: 1200, showConfirmButton: false });
      },
      error: err  => {
        console.error('Error al actualizar puesto', err);
        Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo actualizar el puesto' });
        
      }
    });
  }

  async eliminarPuesto(id: number): Promise<void> {
    const res = await Swal.fire({
      title: '¿Eliminar puesto?',
      text: 'Esta acción no se puede deshacer',
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar'
    });

    if (!res.isConfirmed) return;

    this.puestoService.eliminarPuesto(id).subscribe({
      next: () => {
        this.cargarPuestos();
        Swal.fire({ icon: 'success', title: 'Puesto Eliminado', timer: 1200, showConfirmButton: false });
      },
      error: err => {
        console.error('Error al eliminar puesto', err);
        Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo eliminar el puesto' });
      }
    });
  }

  getDias(puesto: Puesto): string {
    try {
      if (!puesto) return '-';
      const dayMap: Record<number, string> = {
        1: 'Lunes',
        2: 'Martes',
        3: 'Miércoles',
        4: 'Jueves',
        5: 'Viernes',
        6: 'Sábado',
        7: 'Domingo'
      };
      const horarios = puesto.horarios && Array.isArray(puesto.horarios)
        ? puesto.horarios
        : [];
      if (!horarios.length) return '-';

      const groupOrder: string[] = [];
      const groups = new Map<string, Set<number>>();
      for (const h of horarios) {
        const key = `${h.horas ?? ''}-${h.turno ?? ''}`;
        if (!groups.has(key)) {
          groups.set(key, new Set<number>());
          groupOrder.push(key);
        }
        if (h.dia) groups.get(key)!.add(h.dia);
      }

      const parts: string[] = [];
      for (const key of groupOrder) {
        const dias = Array.from(groups.get(key) || []).sort((a, b) => a - b);
        if (!dias.length) continue;
        const min = dias[0];
        const max = dias[dias.length - 1];
        const start = dayMap[min] || '';
        const end = dayMap[max] || '';
        if (!start || !end) continue;
        parts.push(min === max ? start : `${start} - ${end}`);
      }

      return parts.length ? parts.join(' / ') : '-';
    } catch (e) {
      return '-';
    }
  }

  getTurnos(puesto: Puesto): string {
    try {
      if (!puesto || !puesto.horarios || !puesto.horarios.length) return '-';
      const ordered = ['Diurno', 'Nocturno', 'Ambos'];
      const unique = new Set<string>();
      puesto.horarios.forEach(h => {
        if (h.turno) unique.add(h.turno);
      });
      const sorted = ordered.filter(t => unique.has(t));
      const extras = [...unique].filter(t => !ordered.includes(t));
      const all = [...sorted, ...extras];
      const display = all.map(t => (t === 'Ambos' ? '24' : t));
      return display.length ? display.join(' / ') : '-';
    } catch (e) {
      return '-';
    }
  }

  // Mismo resumen que en Asignaciones: multi-grupo, con "H" tras las horas y un grupo por línea.
  getResumenPuestoCompacto(puesto: any): string {
    try {
      if (!puesto || !puesto.horarios || !puesto.horarios.length) return puesto?.resumen || '-';
      const dayMap: any = { 1: 'L', 2: 'M', 3: 'X', 4: 'J', 5: 'V', 6: 'S', 7: 'D' };
      const groups: Record<string, { horas: number; turno: string; dias: number[] }> = {};
      puesto.horarios.forEach((h: any) => {
        const horasVal = Number(h.horas) || 0;
        const turnoVal = (h.turno || '').toString();
        const key = `${horasVal}-${turnoVal}`;
        if (!groups[key]) groups[key] = { horas: horasVal, turno: turnoVal, dias: [] };
        if (h.dia && groups[key].dias.indexOf(h.dia) === -1) groups[key].dias.push(h.dia);
      });
      const letter = (turno: string): string => {
        const t = turno.toLowerCase();
        if (t.startsWith('d')) return 'D';
        if (t.startsWith('n')) return 'N';
        return '';  // 24h/Ambos: sin letra de turno (evita la doble H "24HH")
      };
      const parts = Object.values(groups)
        .map(g => {
          const ordered = g.dias.sort((a: number, b: number) => a - b);
          const first = ordered.length ? (dayMap[ordered[0]] || '') : '';
          const last = ordered.length ? (dayMap[ordered[ordered.length - 1]] || '') : '';
          const diasStr = ordered.length <= 1 ? first : `${first}${last}`;
          const base = `${g.horas}H${letter(g.turno)}`.trim();
          return diasStr ? `${base} ${diasStr}` : base;
        })
        .sort((a, b) => {
          const numA = parseInt(a, 10);
          const numB = parseInt(b, 10);
          return (isNaN(numA) ? 0 : numA) - (isNaN(numB) ? 0 : numB);
        });
      const cant = puesto.cantidad_puestos ? `${puesto.cantidad_puestos}` : '';
      const body = parts.join('\n');
      if (cant && body) return `${cant} ${body}`;
      if (cant) return `${cant}`;
      return body || '-';
    } catch (e) {
      return puesto?.resumen || '-';
    }
  }

  getHoras(puesto: Puesto): string {
    try {
      const horarios = puesto?.horarios || [];
      const horasUnicas = Array.from(new Set(horarios
        .map(h => Number(h.horas))
        .filter(h => !isNaN(h)))) as number[];

      if (horasUnicas.length) {
        return horasUnicas.map(h => h.toString()).join(' / ');
      }

      if (puesto.horas_trabajo !== undefined && puesto.horas_trabajo !== null) {
        return puesto.horas_trabajo.toString();
      }

      return '-';
    } catch (e) {
      return '-';
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files && input.files[0];
    if (!file) return;

    this.puestoService.importPuestosAsignaciones(file, this.clienteSeleccionado || undefined).subscribe({
      next: (res) => {
        const resumen = `Filas: ${res?.filas_validas || 0}/${res?.total_filas || 0}`
          + `, Personas creadas: ${res?.personas_creadas || 0}`
          + `, Puestos creados: ${res?.puestos_creados || 0}`
          + `, Horarios creados: ${res?.horarios_creados || 0}`
          + `, Asignaciones creadas: ${res?.asignaciones_creadas || 0}`
          + `, Asignaciones actualizadas: ${res?.asignaciones_actualizadas || 0}`;
        const errores = Array.isArray(res?.errores) ? res.errores : [];
        const erroresHtml = errores.length
          ? `<div style="text-align:left;max-height:220px;overflow:auto;margin-top:8px;">
                <strong>Errores:</strong>
                <ul style="margin:6px 0 0 18px;">${errores.map((e: string) => `<li>${e}</li>`).join('')}</ul>
             </div>`
          : '';
        Swal.fire({ icon: 'success', title: 'Importacion', html: `${resumen}${erroresHtml}` });
        if (this.clienteSeleccionado) {
          this.cargarPuestos();
        }
      },
      error: (err) => {
        const msg = err?.error?.error || 'No se pudo importar';
        Swal.fire({ icon: 'error', title: 'Error', text: msg });
      }
    });

    input.value = '';
  }

  abrirNovedad(): void {
    const dialogRef = this.dialog.open(NovedadPuestoDialogComponent, {
      width: '760px',
      maxWidth: '95vw',
      data: {
        puestos: this.puestosMostrados,
        clienteNombre: this.clienteSeleccionadoNombre,
        fecha: this.fechaReporteNovedad,
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (!result) return;
      this.novedadService.crearNovedad(result).subscribe({
        next: () => {
          const esCierre = (result.novedad || '').toString().toUpperCase() === 'CIERRE';
          const esApertura = (result.novedad || '').toString().toUpperCase() === 'APERTURA';
          Swal.fire({
            icon: 'success',
            title: 'Novedad registrada',
            text: esCierre ? 'El puesto fue marcado como Cerrado.' : (esApertura ? 'El puesto fue reactivado.' : ''),
            timer: 1600,
            showConfirmButton: false
          });
          // refresca para reflejar estado del puesto (cerrado/reactivado)
          this.cargarPuestos();
        },
        error: (err) => {
          const msg = err?.error?.detail || 'No se pudo registrar la novedad';
          Swal.fire({ icon: 'error', title: 'Error', text: msg });
        }
      });
    });
  }

  verNovedades(): void {
    this.dialog.open(NovedadPuestoListDialogComponent, {
      width: '1100px',
      maxWidth: '95vw',
      data: { fecha: this.fechaReporteNovedad || this.hoyISO() }
    });
  }

  descargarNovedadesExcel(): void {
    const fecha = this.fechaReporteNovedad || this.hoyISO();
    const [anio, mes] = fecha.split('-');
    this.novedadService.descargarExcel(fecha).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `reporte_novedades_${mes}_${anio}.xlsx`;
        a.click();
        window.URL.revokeObjectURL(url);
      },
      error: () => {
        Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo descargar el reporte' });
      }
    });
  }

}


