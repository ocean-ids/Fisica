import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { FormsModule } from '@angular/forms';
import { PuestoService } from '../../services/puesto.service';
import { Puesto } from '../../models';
import { InstalacionService } from '../../services/instalacion.service';
import { Instalacion } from '../../models';


@Component({
  selector: 'app-puestos',
  imports: [
    CommonModule,
    MatTableModule,
    MatButtonModule,
     MatIconModule,
     MatCardModule,
     MatSelectModule,
     MatFormFieldModule,
      FormsModule],
  templateUrl: './puestos.component.html',
  styleUrl: './puestos.component.css'
})
export class PuestosComponent implements OnInit {
  puestos: Puesto[] = [];
  Instalaciones: Instalacion[] = [];
  instalacionSeleccionada: number | null = null;
  displayedColumns: string[] = ['nombre', 'horas_trabajo','acciones'];

  mostrarFormulario = false;
  puestoEditando: Puesto | null = null;

  nuevoPuesto: Puesto = {
    nombre: '',
    horas_trabajo: 0,
    instalacion_id: 0
  };

  constructor(
    private puestoService: PuestoService,
    private instalacionService: InstalacionService
  ) {}

  ngOnInit(): void {
    this.cargarInstalaciones();
  }

  cargarInstalaciones(): void {
    this.instalacionService.getInstalaciones().subscribe({
      next: (data) => this.Instalaciones = data,
      error: (err) => console.error('Error al cargar instalaciones', err)
    });
  }

  cargarPuestos(): void {
    if (this.instalacionSeleccionada) {
      this.puestoService.getPuestosPorInstalacion(this.instalacionSeleccionada).subscribe({
        next: data => this.puestos = data,
        error: err => console.error('Error al cargar puestos:', err)
      });
    }
  }

  abrirFormularioNuevo(puesto?: Puesto): void {
    this.mostrarFormulario = true;
    if(puesto){
      this.puestoEditando = puesto;
      this.nuevoPuesto = {...puesto};
    } else {
      this.puestoEditando = null;
      this.nuevoPuesto = {
        nombre: '',
        horas_trabajo: 0,
        instalacion_id: this.instalacionSeleccionada || 0
      };
    }
  }

  cerrarFormulario(): void {
    this.mostrarFormulario = false;
    this.puestoEditando = null;
  }

  guardarPuesto(): void {
    if (this.puestoEditando?.id) {
      this.actualizarPuesto(this.puestoEditando.id, this.nuevoPuesto);
    } else {
      this.crearPuesto(this.nuevoPuesto);
    }
  }

  crearPuesto(puesto: Puesto): void{
    puesto.instalacion_id = this.instalacionSeleccionada || 0;
    this.puestoService.crearPuesto(puesto).subscribe({
      next: () => {
        this.cargarPuestos();
        this.cerrarFormulario();
      },
      error: (err) => console.error('Error al crear puesto', err)
    });
  }

  actualizarPuesto(id: number, puesto: Puesto): void {
    this.puestoService.actualizarPuesto(id, puesto).subscribe({
      next: () => {
        this.cargarPuestos();
        this.cerrarFormulario();
      },
      error: err  => console.error('Error al actualizar puesto', err)
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

}

