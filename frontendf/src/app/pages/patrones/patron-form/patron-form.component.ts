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
      codigo: [data?.codigo || '', [Validators.required, Validators.pattern(/^\d{3}$/), Validators.maxLength(3), Validators.minLength(3)]],
      secuencia: [data?.secuencia?.join('-') || '', [Validators.required, Validators.pattern(/^(?:[DNF]{1,7}|[DNF](?:-[DNF]){0,6})$/)]]
    });
  }

  
  onCodigoInput(event: Event): void{
    const input = event.target as HTMLInputElement;
    input.value = input.value.replace(/\D/g, '').slice(0, 3);
    this.patronForm.get('codigo')?.setValue(input.value, { emitEvent: false});
  }

  onSecuenciaInput(event: Event): void {
    const input = event.target as HTMLInputElement;
    let raw = input.value.toUpperCase().replace(/[^DNF\-]/g, '').replace(/\-+/g, '-');
    raw = raw.replace(/^\-+/, '').replace(/\-+$/, '');
    const hadHyphen = raw.includes('-');
    let tokens = hadHyphen ? raw.split('-').map(t => t.trim()).filter(t => t.length > 0) : raw.split('').filter(t => t.length > 0);
    if (tokens.length > 7) tokens = tokens.slice(0, 7);
    const val = hadHyphen ? tokens.join('-') : tokens.join('');
    input.value = val;
    this.patronForm.get('secuencia')?.setValue(val, { emitEvent: false });
  }

  onSubmit(): void {
    if (this.patronForm.valid) {
      const patron: PatronAsignacion = {
        codigo: this.patronForm.value.codigo,
        secuencia: (() => {
          const raw = (this.patronForm.value.secuencia as string) || '';
          if (raw.includes('-')) return raw.split('-').map((s: string) => s.trim()).filter((s: string) => s.length > 0);
          return raw.split('').map((s: string) => s.trim()).filter((s: string) => s.length > 0);
        })()
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
