import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatInputModule } from '@angular/material/input';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { FormsModule } from '@angular/forms';
import { PuestoService } from '../../services/puesto.service';
import { Puesto } from '../../models';
import { ClienteService } from '../../services/cliente.service';
import { Cliente } from '../../models';
import { PuestoFormComponent } from './puesto-form/puesto-form.component';
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
  clienteFiltro = '';

  constructor(
    private puestoService: PuestoService,
    private clienteService: ClienteService,
    private dialog: MatDialog
  ) {}

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
    const term = this.clienteFiltro.trim().toLowerCase();
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

  cargarPuestos(): void {
    if (this.clienteSeleccionado) {
      this.puestoService.getPuestosPorCliente(this.clienteSeleccionado).subscribe({
        next: data => this.puestos = data,
        error: err => console.error('Error al cargar puestos:', err)
      });
    }
  }

  abrirFormularioNuevo(puesto?: Puesto): void {
    const dialogRef = this.dialog.open(PuestoFormComponent, {
      width: '500px',
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
      const display = all.map(t => (t === 'Ambos' ? '24h' : t));
      return display.length ? display.join(' / ') : '-';
    } catch (e) {
      return '-';
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

}


