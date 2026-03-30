import { CommonModule } from '@angular/common';
import { Component, Inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { Persona } from '../../../models/persona.model';
import { PersonaService } from '../../../services/persona.service';

@Component({
  selector: 'app-sacafranco-personas-modal',
  standalone: true,
  imports: [CommonModule, FormsModule, MatDialogModule, MatFormFieldModule, MatInputModule, MatButtonModule],
  templateUrl: './sacafranco-personas-modal.component.html',
  styleUrl: './sacafranco-personas-modal.component.css'
})
export class SacafrancoPersonasModalComponent implements OnInit {
  personas: Persona[] = [];
  selectedId: number | null = null;

  constructor(
    private dialogRef: MatDialogRef<SacafrancoPersonasModalComponent, { personaId: number } | null>,
    private personaService: PersonaService,
    @Inject(MAT_DIALOG_DATA) public data: { personas?: Persona[] } | null
  ) {}

  ngOnInit(): void {
    if (this.data?.personas && this.data.personas.length) {
      this.personas = this.data.personas.filter(p => (p.tipo || '').toString().toUpperCase() === 'SACAFRANCO');
      return;
    }

    this.personaService.getPersonas({ tipo: 'SACAFRANCO' }).subscribe({
      next: list => {
        this.personas = list || [];
      },
      error: () => {
        this.personas = [];
      }
    });
  }

  selectPersona(id: number | null | undefined): void {
    if (!id) return;
    this.selectedId = id;
  }

  confirm(): void {
    if (!this.selectedId) return;
    this.dialogRef.close({ personaId: this.selectedId });
  }

  cancel(): void {
    this.dialogRef.close(null);
  }
}
