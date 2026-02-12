import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { FormsModule } from '@angular/forms';
import { PuestoService } from '../../services/puesto.service';
import { Puesto } from '../../models';
import { ClienteService } from '../../services/cliente.service';
import { Cliente } from '../../models';
import { PuestoFormComponent } from './puesto-form/puesto-form.component';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatMenuModule } from '@angular/material/menu';


@Component({
  selector: 'app-puestos',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatButtonModule,
     MatIconModule,
     MatCardModule,
     MatSelectModule,
     MatFormFieldModule,
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
  clienteSeleccionado: number | null = null;

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
      next: (data) => this.clientes = data,
      error: (err) => console.error('Error al cargar clientes', err)
    });
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
        alert('Puesto creado exitosamente');
        this.cargarPuestos();
      },
      error: (err) => {
        console.error('Error al crear puesto', err);
        alert('Error al crear puesto');
      }
    });
  }

  actualizarPuesto(id: number, data: any): void {
    this.puestoService.actualizarPuesto(id, data).subscribe({
      next: () => {
        alert('Puesto actualizado exitosamente');
        this.cargarPuestos();
      },
      error: err  => {
        console.error('Error al actualizar puesto', err);
        alert('Error al actualizar puesto');
      }
    });
  }

  eliminarPuesto(id: number): void {
    if(confirm('¿Estás seguro de que deseas eliminar este puesto?')) {
      this.puestoService.eliminarPuesto(id).subscribe({
        next: () => this.cargarPuestos(),
        error: err => console.error('Error al eliminar puesto', err)
        
      });
    }
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
      const diasNums: number[] = puesto.horarios && Array.isArray(puesto.horarios)
        ? Array.from(new Set(puesto.horarios.map(h => h.dia))) as number[]
        : [];
      if (!diasNums.length) return '-';

      const sorted = diasNums.sort((a, b) => a - b);
      const weekdayRange = [1, 2, 3, 4, 5];
      const hasWeekdaysStrict = weekdayRange.every(d => sorted.includes(d));
      const hasWeekdaySpan = sorted.includes(1) && sorted.includes(5);
      const useWeekdays = hasWeekdaysStrict || hasWeekdaySpan;
      const remaining = useWeekdays ? sorted.filter(d => !weekdayRange.includes(d)) : sorted;

      const parts: string[] = [];
      if (useWeekdays) parts.push('Lunes - Viernes');
      const extras = remaining
        .map(n => dayMap[n] || '')
        .filter(Boolean);
      if (extras.length) parts.push(extras.join(' / '));

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
      return all.length ? all.join(' / ') : '-';
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


