import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PersonalConsolaComponent } from './personal-consola.component';

describe('PersonalConsolaComponent', () => {
  let component: PersonalConsolaComponent;
  let fixture: ComponentFixture<PersonalConsolaComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PersonalConsolaComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(PersonalConsolaComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
