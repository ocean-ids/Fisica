import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Horario } from '../../models/horario.models';
import { HorarioService } from '../../services/horario.service';

@Component({
  selector: 'app-horarios',
  imports: [CommonModule, FormsModule],
  templateUrl: './horarios.component.html',
  styleUrl: './horarios.component.css'
})
export class HorariosComponent implements OnInit{

  horarios: Horario[] = [];
  mostrarModal = false;
  modoEdicion = false;
  horarioSeleccionado: Horario | null = null;

  formulario: Horario = {
    denominativo: '',
    hora_ingreso: '',
    hora_salida: ''
  };

  constructor(private horarioService: HorarioService ){}

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
    this.mostrarModal = true;
    if (horario){
      this.modoEdicion = true;
      this.horarioSeleccionado = horario;
      this.formulario = {...horario};
    }else{
      this.modoEdicion = false;
      this.horarioSeleccionado = null;
      this.limpiarFormulario();
    }
  }

  cerrarModal(): void{
    this.mostrarModal = false;
    this.modoEdicion = false;
    this.horarioSeleccionado = null;
    this.limpiarFormulario();
  }

  limpiarFormulario(): void{
    this.formulario = {
      denominativo: '',
      hora_ingreso: '',
      hora_salida: ''
    };
  }

  guardarHorario(): void{
    if (this.modoEdicion && this.horarioSeleccionado?.id){

      this.horarioService.actualizarHorario(this.horarioSeleccionado.id, this.formulario).subscribe({
        next: () =>{
          alert('Horario actualizado exitosamente');
          this.cargarHorarios();
          this.cerrarModal();
        },
        error: (err) =>{
          console.error('Error al actualizar horarios: ', err);
          alert('Error al actualizar el horario');
          
        }
      });
    } else{
      this.horarioService.crearHorario(this.formulario).subscribe({
        next: () =>{
          alert('Horario creado exitosamente');
          this.cargarHorarios();
          this.cerrarModal();
        },
        error:(err) => {
          console.error('Error al crear horario', err);
          alert('Error al crear horario');
        }
      });
    }
  }

  eliminarHorario(id: number): void{
    if(confirm('¿Estas seguro de eliminar este horario?')){
      this.horarioService.eliminarHorario(id).subscribe({
        next: () => {
          alert('Horario eliminado correctamente');
          this.cargarHorarios();
        },
        error: (err) =>{
          console.error('Error al eliminar horario:', err);
          alert('Error al eliminar horario. Puede que este en uso.')
        }
      });
    }
  }

}
