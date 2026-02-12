import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import {Persona} from '../../models/persona.model'
import { PersonaService } from '../../services/persona.service';
import { PersonaFormComponent } from './persona-form/persona-form.component';
import Swal from 'sweetalert2';

@Component({
  selector: 'app-personas',
  standalone: true,
  imports: [CommonModule, MatTableModule, MatButtonModule, MatIconModule, MatCardModule, MatDialogModule, MatSlideToggleModule],
  templateUrl: './personas.component.html',
  styleUrl: './personas.component.css'
})
export class PersonasComponent implements OnInit {
  personas: Persona[] = []

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
        this.cargarPersonas();
        Swal.fire({ icon: 'success', title: 'Creada', timer: 1200, showConfirmButton: false });
      },
      error: (error) => {
        console.error('Error al crear persona:', error);
        Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo crear' });
      }
    });
  }

  actualizarPersona(id: number, data: any): void {
    this.personaService.updatePersona(id, data).subscribe({
      next: () => {
        this.cargarPersonas();
        Swal.fire({ icon: 'success', title: 'Actualizada', timer: 1200, showConfirmButton: false });
      },
      error: (error) => {
        console.error('Error al actualizar persona:', error);
        Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo actualizar' });
      }
    });
  }

  async confirmarEliminar(persona: Persona): Promise<void> {
    const res = await Swal.fire({
      title: '¿Eliminar persona?',
      text: `Se eliminará ${persona.nombres} ${persona.apellidos}`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar'
    });

    if (!res.isConfirmed || !persona.id) return;

    this.personaService.deletePersona(persona.id).subscribe({
      next: () => {
        this.cargarPersonas();
        Swal.fire({ icon: 'success', title: 'Eliminada', timer: 1200, showConfirmButton: false });
      },
      error: (error) => {
        console.error('Error al eliminar persona:', error);
        Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo eliminar' });
      }
    });
  }

  toggleActive(persona: Persona, checked: boolean): void {
    if (!persona?.id) return;
    const id = persona.id;
    if (checked) {
      this.personaService.enablePersona(id).subscribe({
        next: () => { persona.is_active = true; },
        error: (err) => {
          console.error('Error habilitando persona', err);
          Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo habilitar' });
        }
      });
    } else {
      this.personaService.disablePersona(id).subscribe({
        next: () => { persona.is_active = false; },
        error: (err) => {
          console.error('Error deshabilitando persona', err);
          Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo deshabilitar' });
        }
      });
    }
  }

}
