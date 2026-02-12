import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { Horario } from '../../models/horario.models';
import { HorarioService } from '../../services/horario.service';
import { HorarioFormComponent } from './horario-form/horario-form.component';
import Swal from 'sweetalert2';

@Component({
  selector: 'app-horarios',
  standalone: true,
  imports: [CommonModule, MatTableModule, MatButtonModule, MatIconModule, MatCardModule, MatDialogModule],
  templateUrl: './horarios.component.html',
  styleUrl: './horarios.component.css'
})
export class HorariosComponent implements OnInit{

  horarios: Horario[] = [];

  constructor(
    private horarioService: HorarioService,
    private dialog: MatDialog
  ){}

  ngOnInit(): void {
    this.cargarHorarios();
  }

  cargarHorarios(): void{
    this.horarioService.obtenerHorarios().subscribe({
      next: (data) => {
        this.horarios = data;
        console.log('horarios cargados:', data);
      },
      error: (err) => console.error('Error al cargar horarios', err)
    });
  }

  abrirModal(horario?: Horario): void {
    const dialogRef = this.dialog.open(HorarioFormComponent, {
      width: '500px',
      data: horario || {}
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        if (horario?.id) {
          this.actualizarHorario(horario.id, result);
        } else {
          this.crearHorario(result);
        }
      }
    });
  }

  crearHorario(data: any): void {
    this.horarioService.crearHorario(data).subscribe({
      next: () => {
        this.cargarHorarios();
        Swal.fire({ icon: 'success', title: 'Creado', timer: 1200, showConfirmButton: false });
      },
      error: (err) => {
        console.error('Error al crear horario', err);
        Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo crear' });
      }
    });
  }

  actualizarHorario(id: number, data: any): void {
    this.horarioService.actualizarHorario(id, data).subscribe({
      next: () => {
        this.cargarHorarios();
        Swal.fire({ icon: 'success', title: 'Actualizado', timer: 1200, showConfirmButton: false });
      },
      error: (err) => {
        console.error('Error al actualizar horarios: ', err);
        Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo actualizar' });
      }
    });
  }

  formatearHora(hora: string): string {
    if (!hora) return '';
    // Si la hora tiene formato HH:MM:SS, extraer solo HH:MM
    return hora.substring(0, 5);
  }

  async eliminarHorario(id: number): Promise<void> {
    const res = await Swal.fire({
      title: '¿Eliminar horario?',
      text: 'Esta acción no se puede deshacer',
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar'
    });

    if (!res.isConfirmed) return;

    this.horarioService.eliminarHorario(id).subscribe({
      next: () => {
        this.cargarHorarios();
        Swal.fire({ icon: 'success', title: 'Eliminado', timer: 1200, showConfirmButton: false });
      },
      error: (err) => {
        console.error('Error al eliminar horario:', err);
        Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo eliminar (puede estar en uso)' });
      }
    });
  }

}
