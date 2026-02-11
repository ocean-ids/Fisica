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
      const dayMap: any = {1: 'Lunes', 2: 'Martes', 3: 'Miércoles', 4: 'Jueves', 5: 'Viernes', 6: 'Sábado', 7: 'Domingo'};
      const diasNums: number[] = (puesto.horarios && Array.isArray(puesto.horarios)) ? Array.from(new Set(puesto.horarios.map(h=>h.dia))) as number[] : [];
      if (!diasNums.length) return '-';
      const names = diasNums.sort((a,b)=>a-b).map(n=> dayMap[n] || '').filter(x=>x);
      return names.length ? names.join(', ') : '-';
    } catch (e) {
      return '-';
    }
  }

  getHoras(puesto: Puesto): string {
    try {
      if (!puesto || !puesto.horarios || !puesto.horarios.length) return '-';
      const dayMap: any = {1: 'L', 2: 'M', 3: 'X', 4: 'J', 5: 'V', 6: 'S', 7: 'D'};
      const groups: Record<string, number[]> = {};
      puesto.horarios.forEach(h => {
        const key = `${h.horas || 0}`; // agrupa por horas
        if (!groups[key]) groups[key] = [];
        if (h.dia && groups[key].indexOf(h.dia) === -1) groups[key].push(h.dia);
      });
      const parts = Object.entries(groups)
        .map(([horas, dias]) => {
          const diasStr = dias.sort((a,b)=>a-b).map(d => dayMap[d] || '').join('');
          return `${horas} ${diasStr}`;
        })
        .sort();
      return parts.length ? parts.join(' / ') : '-';
    } catch (e) {
      return '-';
    }
  }

}


