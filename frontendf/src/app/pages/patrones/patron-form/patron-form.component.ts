import { Component, Inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators, AbstractControl, ValidationErrors } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { PatronAsignacionService } from '../../../services/patron-asignacion.service';
import { PatronAsignacion } from '../../../models/asignacion.model';
import { CommonModule } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-patron-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, MatFormFieldModule, MatDialogModule, MatInputModule, MatButtonModule],
  templateUrl: './patron-form.component.html',
  styleUrl: './patron-form.component.css'
})
export class PatronFormComponent {
  patronForm: FormGroup;

  constructor(
    private fb: FormBuilder,
    private dialogRef: MatDialogRef<PatronFormComponent>,
    @Inject(MAT_DIALOG_DATA) public data: PatronAsignacion | null,
    private patronService: PatronAsignacionService
  ) {
    this.patronForm = this.fb.group({
      codigo: [data?.codigo || '', [Validators.required, Validators.pattern(/^\d{3,4}$/)]],
      secuencia: [data?.secuencia?.join('-') || '', [Validators.required, this.secuenciaValidator]]
    });
  }

  // Validador personalizado para la secuencia (texto separado por guiones)
  private secuenciaValidator(control: AbstractControl): ValidationErrors | null {
    const val = control.value as string;
    if (!val || typeof val !== 'string') return { required: true };
    const tokens = val.split('-').map(t => t.trim().toUpperCase()).filter(t => t.length > 0);
    if (tokens.length === 0) return { invalidSequence: 'La secuencia no puede estar vacía' };
    const allowed = new Set(['D', 'N', 'F', '-']);
    for (const t of tokens) {
      if (!allowed.has(t)) return { invalidSequence: `Símbolo no permitido: ${t}` };
    }
    return null;
  }

  onSubmit(): void {
    if (this.patronForm.valid) {
      const patron: PatronAsignacion = {
        codigo: this.patronForm.value.codigo,
        secuencia: (this.patronForm.value.secuencia as string).split('-').map((s: string) => s.trim())
      };
      if (this.data && this.data.id) {
        this.patronService.actualizarPatron(this.data.id, patron).subscribe(() => this.dialogRef.close(true));
      } else {
        this.patronService.crearPatron(patron).subscribe(() => this.dialogRef.close(true));
      }
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
