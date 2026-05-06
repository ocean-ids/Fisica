import { CommonModule } from '@angular/common';
import { Component, Inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { Persona } from '../../../models/persona.model';
import { PersonaService } from '../../../services/persona.service';


@Component({
  selector: 'app-sacafranco-personas-modal',
  standalone: true,
  imports: [CommonModule, FormsModule, MatDialogModule, MatFormFieldModule, MatInputModule, MatSelectModule, MatButtonModule],
  templateUrl: './sacafranco-personas-modal.component.html',
  styleUrl: './sacafranco-personas-modal.component.css'
})
export class SacafrancoPersonasModalComponent implements OnInit {
  personas: Persona[] = [];
  personasAll: Persona[] = [];
  selectedId: number | null = null;
  provincias: Array<{ id: number; nombre: string }> = [];
  selectedProvinciaId: number | null = null;
  assignedIds = new Set<number>();

  constructor(
    private dialogRef: MatDialogRef<SacafrancoPersonasModalComponent, { personaId: number; provinciaId: number | null } | null>,
    private personaService: PersonaService,
    @Inject(MAT_DIALOG_DATA) public data: { personas?: Persona[]; assignedPersonaIds?: number[]; provincias?: Array<{ id: number; nombre: string }>; provinciaId?: number | null } | null
  ) {}

  private applyProvinciaFilter(): void {
    if (!this.selectedProvinciaId){
      this.personas = [];
      return;
    }
    this.personas = (this.personasAll || [])
      .filter(p => p.provincia === this.selectedProvinciaId);
  }

  onProvinciaChange(): void {
    this.selectedId = null;
    this.applyProvinciaFilter();
  }

  ngOnInit(): void {
    if (this.data?.assignedPersonaIds?.length) {
      this.assignedIds = new Set(this.data.assignedPersonaIds);
    }
    if (this.data?.provincias?.length) {
      this.provincias = this.data.provincias;
    }
    if (this.data?.provinciaId !== undefined) {
      this.selectedProvinciaId = this.data.provinciaId ?? null;
    }
    if (this.data?.personas && this.data.personas.length) {
      this.personas = this.data.personas.filter(p => (p.tipo || '').toString().toUpperCase() === 'SACAFRANCO');
      this.applyProvinciaFilter();
      return;
    }
    

    this.personaService.getPersonas({ tipo: 'SACAFRANCO' }).subscribe({
      next: list => {
        this.personasAll = list || [];
        this.applyProvinciaFilter();
      },
      error: () => {
        this.personasAll = [];
        this.applyProvinciaFilter();
      }
    });
  }


  selectPersona(id: number | null | undefined): void {
    if (!id) return;
    this.selectedId = id;
  }

  isAssigned(personaId?: number | null): boolean {
    if (!personaId) return false;
    return this.assignedIds.has(personaId);
  }

  confirm(): void {
    if (!this.selectedId) return;
    this.dialogRef.close({ personaId: this.selectedId, provinciaId: this.selectedProvinciaId });
  }

  cancel(): void {
    this.dialogRef.close(null);
  }
}
