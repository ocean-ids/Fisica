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
  cantones: Array<{ id: number | null; nombre: string }> = [];
  selectedCantonId: number | null = null;
  assignedIds = new Set<number>();

  constructor(
    private dialogRef: MatDialogRef<SacafrancoPersonasModalComponent, { personaId: number; cantonId: number | null } | null>,
    private personaService: PersonaService,
    @Inject(MAT_DIALOG_DATA) public data: { personas?: Persona[]; assignedPersonaIds?: number[]; cantones?: Array<{ id: number | null; nombre: string }>; cantonId?: number | null } | null
  ) {}

  private applyCantonFilter(): void {
    if (this.selectedCantonId === null){
      this.personas = [];
      return;
    }
    const normalizeName = (value: string | null | undefined): string => {
      if (!value) return '';
      return value
        .toString()
        .trim()
        .toUpperCase()
        .replace(/[^A-Z0-9]+/g, '');
    };
    const selectedCanton = (this.cantones || []).find(c => c.id === this.selectedCantonId);
    const selectedName = normalizeName(selectedCanton?.nombre || '');
    this.personas = (this.personasAll || []).filter(p => {
      const personaCantonId = (p as any).canton;
      if (personaCantonId === this.selectedCantonId) return true;
      if (!selectedName) return false;
      const personaCantonName = normalizeName((p as any).canton_nombre || '');
      return personaCantonName && personaCantonName === selectedName;
    });
  }

  onCantonChange(): void {
    this.selectedId = null;
    this.applyCantonFilter();
  }

  ngOnInit(): void {
    if (this.data?.assignedPersonaIds?.length) {
      this.assignedIds = new Set(this.data.assignedPersonaIds);
    }
    if (this.data?.cantones?.length) {
      this.cantones = this.data.cantones;
    }
    if (this.data?.cantonId !== undefined) {
      this.selectedCantonId = this.data.cantonId ?? null;
    }
    if (this.data?.personas && this.data.personas.length) {
      this.personas = this.data.personas.filter(p => (p.tipo || '').toString().toUpperCase() === 'SACAFRANCO');
      this.applyCantonFilter();
      return;
    }
    

    this.personaService.getPersonas({ tipo: 'SACAFRANCO' }).subscribe({
      next: list => {
        this.personasAll = list || [];
        this.applyCantonFilter();
      },
      error: () => {
        this.personasAll = [];
        this.applyCantonFilter();
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
    this.dialogRef.close({ personaId: this.selectedId, cantonId: this.selectedCantonId });
  }

  cancel(): void {
    this.dialogRef.close(null);
  }
}
