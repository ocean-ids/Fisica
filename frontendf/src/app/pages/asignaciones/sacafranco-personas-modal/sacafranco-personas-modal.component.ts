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
  personasFiltradas: Persona[] = [];
  filtroNombre: string = '';
  selectedId: number | null = null;
  cantones: Array<{ id: number | null; nombre: string }> = [];
  selectedCantonId: number | null = null;
  assignedIds = new Set<number>();

  constructor(
    private dialogRef: MatDialogRef<SacafrancoPersonasModalComponent, { personaId: number; cantonId: number | null } | null>,
    private personaService: PersonaService,
    @Inject(MAT_DIALOG_DATA) public data: { personas?: Persona[]; assignedPersonaIds?: number[]; cantones?: Array<{ id: number | null; nombre: string }>; cantonId?: number | null } | null
  ) {}

  private normalizeText(value: string | null | undefined): string {
    if (!value) return '';
    return value
      .toString()
      .trim()
      .toUpperCase()
      .replace(/[^A-Z0-9]+/g, '');
  }

  private applyFilters(): void {
    // Ya no se filtra por cantón: se muestran todas las personas sacafranco.
    const all = this.personasAll || [];
    const q = this.normalizeText(this.filtroNombre);
    if (!q) {
      this.personasFiltradas = all;
      return;
    }
    this.personasFiltradas = all.filter(p => {
      const fullName = this.normalizeText(`${p.apellidos || ''} ${p.nombres || ''}`);
      return fullName.includes(q);
    });
  }

  getProvincia(p: Persona): string {
    return ((p as any)?.provincia_nombre || '').toString();
  }

  onNombreFilterChange(): void {
    this.selectedId = null;
    this.applyFilters();
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
      this.personasAll = this.data.personas.filter(p => (p.tipo || '').toString().toUpperCase() === 'SACAFRANCO');
      this.personas = this.personasAll;
      this.applyFilters();
      return;
    }
    

    this.personaService.getPersonas({ tipo: 'SACAFRANCO' }).subscribe({
      next: list => {
        this.personasAll = list || [];
        this.personas = this.personasAll;
        this.applyFilters();
      },
      error: () => {
        this.personasAll = [];
        this.personas = [];
        this.applyFilters();
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
    this.dialogRef.close({ personaId: this.selectedId, cantonId: null });
  }

  cancel(): void {
    this.dialogRef.close(null);
  }
}
