import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import {Persona} from '../../models/persona.model'
import { PersonaService } from '../../services/persona.service';
import { PersonaFormComponent } from './persona-form/persona-form.component';

@Component({
  selector: 'app-personas',
  standalone: true,
  imports: [CommonModule, MatTableModule, MatButtonModule, MatIconModule, MatCardModule, MatDialogModule],
  templateUrl: './personas.component.html',
  styleUrl: './personas.component.css'
})
export class PersonasComponent implements OnInit {
  personas: Persona[] = []
  showDeleteModal: boolean = false;
  personaEliminar: Persona | null = null;

  constructor(
    private personaService: PersonaService,
    private dialog: MatDialog
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

  abrirModal(persona?: Persona): void {
    const dialogRef = this.dialog.open(PersonaFormComponent, {
      width: '500px',
      data: persona || {}
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        if (persona?.id) {
          this.actualizarPersona(persona.id, result);
        } else {
          this.crearPersona(result);
        }
      }
    });
  }

  crearPersona(data: any): void {
    this.personaService.createPersona(data).subscribe({
      next: () => {
        alert('Persona creada exitosamente');
        this.cargarPersonas();
      },
      error: (error) => {
        console.error('Error al crear persona:', error);
        alert('Error al crear persona');
      }
    });
  }

  actualizarPersona(id: number, data: any): void {
    this.personaService.updatePersona(id, data).subscribe({
      next: () => {
        alert('Persona actualizada exitosamente');
        this.cargarPersonas();
      },
      error: (error) => {
        console.error('Error al actualizar persona:', error);
        alert('Error al actualizar persona');
      }
    });
  }

  confirmarEliminar(persona: Persona): void {
    this.personaEliminar = persona;
    this.showDeleteModal = true;
  }

  eliminarPersona(): void {
    if (this.personaEliminar && this.personaEliminar.id) {
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
