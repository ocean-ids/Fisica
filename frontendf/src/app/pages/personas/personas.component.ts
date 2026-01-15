import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {Persona} from '../../models/persona.model'
import { PersonaService } from '../../services/persona.service';

@Component({
  selector: 'app-personas',
  imports: [CommonModule, FormsModule],
  templateUrl: './personas.component.html',
  styleUrl: './personas.component.css'
})
export class PersonasComponent implements OnInit {
  personas: Persona[] = []
  showModal: boolean = false;
  showDeleteModal: boolean = false;
  isEditMode: boolean = false;


  nuevaPersona: any ={
    nombres: '',
    apellidos: '',
    cedula: '',
    tipo: ''
  };

  personaSeleccionada: any = null;
  personaEliminar: any = null;


  constructor(
    private personaService: PersonaService
  ){}

  ngOnInit(): void {
   this.cargarPersonas();
  }

  cargarPersonas(): void {
    this.personaService.getPersonas().subscribe({
      next: (data) =>{
        this.personas = data;
        console.log('Personas cargadas', this.personas);
      },
      error: (error) => console.error('Error al cargar',error)
      
    });
  }

  abrirModal(): void {
    this.isEditMode = false;
    this.nuevaPersona = {
      nombres: '',
      apellidos: '',
      cedula: '',
      tipo: ''
    };
    this.showModal = true;
  }

  editarPersona(persona: Persona): void {
    this.isEditMode = true;
    this.personaSeleccionada = persona;
    this.nuevaPersona = {
      nombres: persona.nombres,
      apellidos: persona.apellidos,
      cedula: persona.cedula,
      tipo: persona.tipo
    };
    this.showModal = true;
  }

  cerrarModal(): void{
    this.showModal = false;
    this. isEditMode = false;
    this.personaSeleccionada = null;
    this.nuevaPersona = {
      nombres: '',
      apellidos: '',
      cedula: '',
      tipo: ''
    }
  };

  guardarPersona(): void {
    if (this.isEditMode && this.personaSeleccionada) {
      
      this.personaService.updatePersona(this.personaSeleccionada.id, this.nuevaPersona).subscribe({
        next: () => {
          console.log('Persona actualizada exitosamente');
          this.cargarPersonas();
          this.cerrarModal();
        },
        error: (error) => console.error('Error al actualizar persona:', error)
      });
    } else {
      
      this.personaService.createPersona(this.nuevaPersona).subscribe({
        next: () => {
          console.log('Persona creada exitosamente');
          this.cargarPersonas();
          this.cerrarModal();
        },
        error: (error) => console.error('Error al crear persona:', error)
      });
    }
  }

  confirmarEliminar(persona: Persona): void {
    this.personaEliminar = persona;
    this.showDeleteModal = true;
  }

  eliminarPersona(): void {
    if (this.personaEliminar) {
      this.personaService.deletePersona(this.personaEliminar.id).subscribe({
        next: () => {
          console.log('Persona eliminada exitosamente');
          this.cargarPersonas();
          this.cancelarEliminar();
        },
        error: (error) => console.error('Error al eliminar persona:', error)
      });
    }
  }

  cancelarEliminar(): void {
    this.showDeleteModal = false;
    this.personaEliminar = null;
  }

}
